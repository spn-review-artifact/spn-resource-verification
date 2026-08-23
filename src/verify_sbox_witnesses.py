#!/usr/bin/env python3
"""Exhaustively verify released forward/inverse S-box Boolean netlists.

This program contains no SAT/SMT synthesis routine.  It parses fixed witnesses,
checks all 16 inputs, reconstructs the released clean-mapping matrices, and
recomputes the manuscript's logical XOR-network CNOT count for forward rows.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "src" / "mapping"
sys.path.insert(0, str(MAPPING))

from classical_to_quantum import classical_to_quantum, verify_circuit  # noqa: E402
from linear_parser import parse_circuit  # noqa: E402


def read_ops(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def inverse_table(table: list[int]) -> list[int]:
    result = [0] * len(table)
    for source, target in enumerate(table):
        result[target] = source
    return result


def row_additions_free_permutation(matrix: list[list[int]]) -> int:
    """Count Gaussian row additions while row swaps are free relabeling."""
    work = [row[:] for row in matrix]
    count = 0
    for column in range(len(work)):
        pivot = next(
            (row for row in range(column, len(work)) if work[row][column]), None
        )
        if pivot is None:
            continue
        if pivot != column:
            work[column], work[pivot] = work[pivot], work[column]
        for row in range(len(work)):
            if row != column and work[row][column]:
                work[row] = [a ^ b for a, b in zip(work[row], work[column])]
                count += 1
    return count


def coefficient_weight(expression: str) -> int:
    return sum(term not in {"", "0", "1"} for term in expression.split("+"))


def inspect(path: Path, table: list[int]) -> dict[str, object]:
    operations = read_ops(path)
    layers, and_depth, and_count = parse_circuit(4, 4, operations)
    mapped = classical_to_quantum(4, 4, and_depth, operations)
    truth_ok = verify_circuit(mapped, table)
    rowops = [
        row_additions_free_permutation(matrix.data)
        for matrix in mapped.state_transform_matrices[:and_depth]
    ]
    output_weight = sum(coefficient_weight(item) for item in layers[-1])
    return {
        "truth_table_check": "pass-16/16" if truth_ok else "fail",
        "and_count": and_count,
        "and_depth": and_depth,
        "logical_cnot": 2 * sum(rowops) + output_weight,
        "mapping_width": mapped.width,
        "row_additions": rowops,
        "output_weight": output_weight,
    }


def verify_all() -> list[dict[str, object]]:
    catalog = json.loads(
        (ROOT / "data" / "reference" / "sboxes.json").read_text(encoding="utf-8")
    )["sboxes"]
    rows: list[dict[str, object]] = []
    failures: list[str] = []
    for name, entry in catalog.items():
        table = [int(character, 16) for character in entry["lut"]]
        forward = inspect(ROOT / entry["forward_netlist"], table)
        inverse_lut = inverse_table(table)
        inverse = inspect(ROOT / entry["inverse_netlist"], inverse_lut)
        reuse_safe_passed = sum(
            (value ^ inverse_lut[table[value]]) == 0 for value in range(16)
        )
        checks = {
            "forward_truth": forward["truth_table_check"] == "pass-16/16",
            "inverse_truth": inverse["truth_table_check"] == "pass-16/16",
            "forward_k": forward["and_count"] == entry["reported_k"],
            "forward_depth": forward["and_depth"] == entry["reported_and_depth"],
            "forward_cnot": forward["logical_cnot"]
            == entry["reported_logical_cnot"],
            "old_state_cleanup": reuse_safe_passed == 16,
        }
        if not all(checks.values()):
            failures.append(f"{name}: {checks}")
        row = {
            "sbox": name,
            "minimum_status": entry["minimum_status"],
            "forward": forward,
            "inverse": inverse,
            "reuse_safe_transition_check": f"pass-{reuse_safe_passed}/16",
            "checks": checks,
        }
        rows.append(row)
        print(
            f"{name:8s} forward={forward['truth_table_check']} "
            f"inverse={inverse['truth_table_check']} k={forward['and_count']} "
            f"AND-depth={forward['and_depth']} CNOT={forward['logical_cnot']} "
            f"cleanup=pass-{reuse_safe_passed}/16"
        )
    if failures:
        raise AssertionError("\n".join(failures))
    print("all released S-box witnesses verified")
    return rows


def main() -> int:
    verify_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
