#!/usr/bin/env python3
"""Reference encoder for 4-bit depth-2 AND-XOR S-boxes.

This implementation provides a transparent path from a 16-nibble LUT to
SMT-LIB2, a SAT witness netlist, and an exhaustive 16-input functional check.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any

import z3


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "reference" / "sboxes.json"


def parse_lut(text: str) -> list[int]:
    """Parse the repository's input-indexed 16-hex-character LUT format."""
    compact = text.strip().replace("_", "").upper()
    if compact.startswith("0X"):
        compact = compact[2:]
    if len(compact) != 16 or any(ch not in "0123456789ABCDEF" for ch in compact):
        raise ValueError("a 4-bit S-box LUT must contain exactly 16 hexadecimal digits")
    values = [int(ch, 16) for ch in compact]
    if sorted(values) != list(range(16)):
        raise ValueError("the LUT must be a permutation of hexadecimal nibbles 0..F")
    return values


def lut_text(values: list[int]) -> str:
    return "".join(f"{value:X}" for value in values)


def load_catalog() -> dict[str, dict[str, Any]]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["sboxes"]


def resolve_target(cipher: str | None, lut: str | None) -> tuple[str, list[int]]:
    if (cipher is None) == (lut is None):
        raise ValueError("select exactly one of --cipher or --lut")
    if lut is not None:
        values = parse_lut(lut)
        return "custom", values
    catalog = load_catalog()
    assert cipher is not None
    matches = {name.lower(): name for name in catalog}
    key = matches.get(cipher.lower())
    if key is None:
        raise ValueError(f"unknown cipher {cipher!r}; choose one of {', '.join(catalog)}")
    return key, parse_lut(catalog[key]["lut"])


def xor_coeff(coefficients: list[z3.BoolRef], values: list[z3.BoolRef]) -> z3.BoolRef:
    result = z3.BoolVal(False)
    for coefficient, value in zip(coefficients, values):
        result = z3.Xor(result, z3.And(coefficient, value))
    return result


def build_fixed_solver(
    target_lut: list[int], k1: int, k2: int
) -> tuple[z3.Solver, dict[str, list[list[z3.BoolRef]]]]:
    """Build the disclosed fixed-shape feasibility encoding."""
    if k1 < 0 or k2 < 0:
        raise ValueError("k1 and k2 must be nonnegative")
    n = m = 4
    solver = z3.Solver()

    a1 = [[z3.Bool(f"a1_{i}_{j}") for j in range(n)] for i in range(k1)]
    b1 = [[z3.Bool(f"b1_{i}_{j}") for j in range(n)] for i in range(k1)]
    a2 = [
        [z3.Bool(f"a2_{i}_{j}") for j in range(n + k1)] for i in range(k2)
    ]
    b2 = [
        [z3.Bool(f"b2_{i}_{j}") for j in range(n + k1)] for i in range(k2)
    ]
    output_width = n + k1 + k2 + 1
    cy = [
        [z3.Bool(f"cy_{output}_{j}") for j in range(output_width)]
        for output in range(m)
    ]

    for gate in range(k1):
        solver.add(z3.Or(*a1[gate]))
        solver.add(z3.Or(*b1[gate]))
    for gate in range(k2):
        solver.add(z3.Or(*a2[gate]))
        solver.add(z3.Or(*b2[gate]))

    for input_value in range(16):
        input_bits = [
            z3.BoolVal(bool((input_value >> bit) & 1)) for bit in range(n)
        ]
        layer1 = [
            z3.And(
                xor_coeff(a1[gate], input_bits),
                xor_coeff(b1[gate], input_bits),
            )
            for gate in range(k1)
        ]
        pool1 = input_bits + layer1
        layer2 = [
            z3.And(
                xor_coeff(a2[gate], pool1),
                xor_coeff(b2[gate], pool1),
            )
            for gate in range(k2)
        ]
        pool2 = pool1 + layer2
        for output in range(m):
            value = xor_coeff(cy[output][:-1], pool2)
            value = z3.Xor(value, cy[output][-1])
            expected = z3.BoolVal(bool((target_lut[input_value] >> output) & 1))
            solver.add(value == expected)

    return solver, {"a1": a1, "b1": b1, "a2": a2, "b2": b2, "cy": cy}


def extract_netlist(
    model: z3.ModelRef,
    variables: dict[str, list[list[z3.BoolRef]]],
    k1: int,
    k2: int,
) -> list[str]:
    """Convert one SAT model into a compact two-input XOR/AND netlist."""
    operations: list[str] = []
    a1, b1 = variables["a1"], variables["b1"]
    a2, b2 = variables["a2"], variables["b2"]
    cy = variables["cy"]

    def selected(variable: z3.BoolRef) -> bool:
        return z3.is_true(model.evaluate(variable, model_completion=True))

    def xor_chain(terms: list[str], prefix: str) -> str | None:
        if not terms:
            return None
        accumulator = terms[0]
        for index, term in enumerate(terms[1:]):
            temporary = f"{prefix}_{index}"
            operations.append(f"{temporary}={accumulator}+{term}")
            accumulator = temporary
        return accumulator

    input_names = [f"X{bit}" for bit in range(4)]
    layer1_names = [f"M1_{gate}" for gate in range(k1)]
    layer2_names = [f"M2_{gate}" for gate in range(k2)]
    pool1_names = input_names + layer1_names
    pool2_names = pool1_names + layer2_names

    for gate in range(k1):
        left = [input_names[j] for j in range(4) if selected(a1[gate][j])]
        right = [input_names[j] for j in range(4) if selected(b1[gate][j])]
        left_name = xor_chain(left, f"TL1_{gate}")
        right_name = xor_chain(right, f"TR1_{gate}")
        if left_name is None or right_name is None:
            raise RuntimeError("model violates the nonempty first-layer operand constraint")
        operations.append(f"{layer1_names[gate]}={left_name}*{right_name}")

    for gate in range(k2):
        left = [
            pool1_names[j] for j in range(4 + k1) if selected(a2[gate][j])
        ]
        right = [
            pool1_names[j] for j in range(4 + k1) if selected(b2[gate][j])
        ]
        left_name = xor_chain(left, f"TL2_{gate}")
        right_name = xor_chain(right, f"TR2_{gate}")
        if left_name is None or right_name is None:
            raise RuntimeError("model violates the nonempty second-layer operand constraint")
        operations.append(f"{layer2_names[gate]}={left_name}*{right_name}")

    for output in range(4):
        terms = [
            pool2_names[j]
            for j in range(4 + k1 + k2)
            if selected(cy[output][j])
        ]
        has_constant = selected(cy[output][-1])
        if terms:
            result_name = xor_chain(terms, f"TY{output}")
            assert result_name is not None
            operations.append(f"Y{output}={result_name}")
        else:
            operations.append(f"TY{output}_z=X0+X0")
            operations.append(f"Y{output}=TY{output}_z")
        if has_constant:
            operations.append(f"Y{output}=Y{output}+1")
    return operations


def evaluate_netlist(operations: list[str], input_value: int) -> int:
    values = {f"X{bit}": (input_value >> bit) & 1 for bit in range(4)}
    values["1"] = 1
    for operation in operations:
        stripped = operation.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lhs, rhs = stripped.replace(" ", "").split("=", 1)
        if "*" in rhs:
            left, right = rhs.split("*", 1)
            values[lhs] = values[left] & values[right]
        elif "+" in rhs:
            left, right = rhs.split("+", 1)
            values[lhs] = values[left] ^ values[right]
        else:
            values[lhs] = values[rhs]
    return sum(values[f"Y{bit}"] << bit for bit in range(4))


def verify_netlist(operations: list[str], target_lut: list[int]) -> bool:
    return all(
        evaluate_netlist(operations, input_value) == target_lut[input_value]
        for input_value in range(16)
    )


def fixed_smt_text(
    name: str, target_lut: list[int], k1: int, k2: int, solver: z3.Solver
) -> str:
    header = (
        f"; target: {name}\n"
        f"; target_lut: {lut_text(target_lut)}\n"
        f"; fixed AND-depth-2 shape: k1={k1}, k2={k2}, total_k={k1 + k2}\n"
        "; generated_by: public reference_smt_encoder.py\n"
        "; purpose: frozen feasibility instance; not a lower-bound certificate\n"
    )
    return header + solver.sexpr() + "\n(check-sat)\n"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def run_fixed(
    name: str,
    target_lut: list[int],
    k1: int,
    k2: int,
    timeout_ms: int,
    seed: int,
) -> tuple[dict[str, Any], z3.Solver, list[str] | None]:
    solver, variables = build_fixed_solver(target_lut, k1, k2)
    solver.set(timeout=timeout_ms, random_seed=seed)
    started = time.perf_counter()
    status = solver.check()
    elapsed = time.perf_counter() - started
    operations = None
    verification = "not-run"
    if status == z3.sat:
        operations = extract_netlist(solver.model(), variables, k1, k2)
        verification = "pass-16/16" if verify_netlist(operations, target_lut) else "fail"
        if verification == "fail":
            raise RuntimeError("the extracted SAT model failed exhaustive verification")
    row: dict[str, Any] = {
        "target": name,
        "target_lut": lut_text(target_lut),
        "k1": k1,
        "k2": k2,
        "total_k": k1 + k2,
        "and_depth_bound": 2,
        "solver_status": str(status),
        "runtime_seconds": round(elapsed, 6),
        "timeout_ms": timeout_ms,
        "random_seed": seed,
        "constraint_count": len(solver.assertions()),
        "smt2_bytes": len(solver.sexpr().encode("utf-8")),
        "truth_table_check": verification,
    }
    return row, solver, operations


def bounded_search(
    name: str,
    target_lut: list[int],
    k_min: int,
    k_max: int,
    timeout_ms: int,
    seed: int,
) -> tuple[dict[str, Any], z3.Solver | None, list[str] | None, tuple[int, int] | None]:
    if not 0 <= k_min <= k_max:
        raise ValueError("require 0 <= k_min <= k_max")
    attempts = []
    selected_solver = None
    selected_operations = None
    selected_shape = None
    lower_search_complete = True
    for total_k in range(k_min, k_max + 1):
        for k1 in range(total_k + 1):
            k2 = total_k - k1
            row, solver, operations = run_fixed(
                name, target_lut, k1, k2, timeout_ms, seed
            )
            attempts.append(row)
            print(
                f"target={name} k={total_k} shape=({k1},{k2}) "
                f"status={row['solver_status']} elapsed={row['runtime_seconds']:.6f}s"
            )
            if row["solver_status"] == "unknown":
                lower_search_complete = False
            if row["solver_status"] == "sat":
                selected_solver = solver
                selected_operations = operations
                selected_shape = (k1, k2)
                break
        if selected_shape is not None:
            break
    result = {
        "mode": "bounded-increasing-k-reference-search",
        "target": name,
        "target_lut": lut_text(target_lut),
        "k_min": k_min,
        "k_max": k_max,
        "timeout_ms_per_attempt": timeout_ms,
        "random_seed": seed,
        "attempts": attempts,
        "first_sat_total_k": sum(selected_shape) if selected_shape else None,
        "first_sat_shape": list(selected_shape) if selected_shape else None,
        "lower_search_complete": lower_search_complete,
        "claim": (
            "minimum-within-disclosed-depth-2-space"
            if selected_shape is not None and lower_search_complete and k_min == 0
            else "first-sat-within-enumerated-k-range"
            if selected_shape is not None and lower_search_complete
            else "feasible-but-minimum-not-proved"
            if selected_shape is not None
            else "no-feasible-instance-found-within-bound"
        ),
    }
    return result, selected_solver, selected_operations, selected_shape


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--cipher", help="catalog name, e.g. PRESENT or uLBC")
    target.add_argument("--lut", help="custom 16-hex-character 4-bit permutation")
    shape = parser.add_argument_group("fixed shape or bounded search")
    shape.add_argument("--k1", type=int)
    shape.add_argument("--k2", type=int)
    shape.add_argument("--k-min", type=int, default=0)
    shape.add_argument("--k-max", type=int)
    parser.add_argument("--timeout-ms", type=int, default=60_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--smt2", type=Path, help="write selected fixed SMT-LIB2")
    parser.add_argument("--netlist", type=Path, help="write selected SAT witness")
    parser.add_argument("--summary-json", type=Path, help="write machine-readable result")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    name, target_lut = resolve_target(args.cipher, args.lut)
    fixed_requested = args.k1 is not None or args.k2 is not None
    if fixed_requested:
        if args.k1 is None or args.k2 is None or args.k_max is not None:
            raise ValueError("fixed mode requires both --k1 and --k2 and no --k-max")
        row, solver, operations = run_fixed(
            name, target_lut, args.k1, args.k2, args.timeout_ms, args.seed
        )
        result: dict[str, Any] = {"mode": "fixed-shape", **row}
        selected_shape = (args.k1, args.k2)
    else:
        if args.k_max is None:
            raise ValueError("provide either --k1/--k2 or --k-max")
        result, solver, operations, selected_shape = bounded_search(
            name,
            target_lut,
            args.k_min,
            args.k_max,
            args.timeout_ms,
            args.seed,
        )

    if args.smt2 is not None:
        if solver is None or selected_shape is None:
            raise RuntimeError("no selected SAT instance is available for SMT export")
        k1, k2 = selected_shape
        write_text(args.smt2, fixed_smt_text(name, target_lut, k1, k2, solver))
        result["smt2_output"] = args.smt2.as_posix()
    if args.netlist is not None:
        if operations is None or selected_shape is None:
            raise RuntimeError("no SAT witness is available for netlist export")
        k1, k2 = selected_shape
        header = [
            f"# target: {name}",
            f"# target_lut: {lut_text(target_lut)}",
            "# generated_by: public reference_smt_encoder.py",
            f"# fixed_configuration: k1={k1}, k2={k2}",
            "# truth_table_check: pass-16/16",
            "",
        ]
        write_text(args.netlist, "\n".join(header + operations + [""]))
        result["netlist_output"] = args.netlist.as_posix()
    if args.summary_json is not None:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    print(json.dumps(result, indent=2))
    if result.get("solver_status") == "sat" or result.get("first_sat_total_k") is not None:
        return 0
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
