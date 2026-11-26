"""Replay reconstructed uLBC logical gate sequences on computational basis states.

Usage: python -B src/verify_r2_ulbc_gate_sequence.py [ARTIFACT_ROOT] [--check-record]
ARTIFACT_ROOT is a checkout of spn-review-artifact/spn-resource-verification.
The AND/erase pair is modeled by its verified Boolean action. The phase
oracle carries an ideal Z sign, without simulating physical measurements.
"""

import argparse
from contextlib import redirect_stdout
from dataclasses import dataclass
import hashlib
from importlib import import_module
import io
import json
from pathlib import Path
import re
import sys

from verify_r2_ulbc import load_reference


def undo(gates):
    inverses = {"and": "erase", "erase": "and"}
    return [
        (inverses.get(kind, kind), *wires)
        for kind, *wires in reversed(gates)
    ]


def execute(gates, state, sign=1):
    for kind, *wires in gates:
        if kind == "x":
            state[wires[0]] ^= 1
        elif kind == "cx":
            source, target = wires
            state[target] ^= state[source]
        elif kind == "relabel":
            left, right = wires
            state[left], state[right] = state[right], state[left]
        elif kind in {"and", "erase"}:
            left, right, target = wires
            product = state[left] & state[right]
            if state[target] != (0 if kind == "and" else product):
                raise AssertionError(f"{kind} precondition failed on {wires}")
            state[target] ^= product
        elif kind == "z":
            if state[wires[0]]:
                sign = -sign
        else:
            raise ValueError(f"Unknown operation {kind}")
    return sign


def matrix_gates(matrix, wires):
    """Match the release's Gaussian row additions with free relabeling."""
    work = [row.copy() for row in matrix]
    reduction = []
    for column in range(len(work)):
        pivot = next(row for row in range(column, len(work)) if work[row][column])
        if pivot != column:
            work[column], work[pivot] = work[pivot], work[column]
            reduction.append(("relabel", wires[column], wires[pivot]))
        for row in range(len(work)):
            if row != column and work[row][column]:
                work[row] = [x ^ y for x, y in zip(work[row], work[column])]
                reduction.append(("cx", wires[column], wires[row]))
    return list(reversed(reduction))


def affine_mask(expression):
    mask = 0
    constant = 0
    for term in expression.split("+"):
        if term == "1":
            constant ^= 1
        elif term and term != "0":
            mask ^= 1 << (int(term[1:]) + (4 if term.startswith("M") else 0))
    return mask, constant


def output_cnot_sources(state_masks):
    """Find linear combinations on the live wires, preferring fewer CNOTs."""
    combinations = {0: ()}
    for wire, mask in enumerate(state_masks):
        if mask:
            for value, sources in list(combinations.items()):
                new_value = value ^ mask
                candidate = (*sources, wire)
                if new_value not in combinations or len(candidate) < len(combinations[new_value]):
                    combinations[new_value] = candidate
    return combinations


@dataclass
class CleanSbox:
    width: int
    gates: list

    def on_wires(self, source, target, scratch):
        mapping = [*source, *scratch[: self.width - 8], *target]
        return [(kind, *(mapping[wire] for wire in wires)) for kind, *wires in self.gates]


def clean_sbox(path, mapper, parser):
    netlist = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    layers, depth, _ = parser.parse_circuit(4, 4, netlist)
    with redirect_stdout(io.StringIO()):
        circuit = mapper.classical_to_quantum(4, 4, depth, netlist)
    masks = [1, 2, 4, 8] + [0] * (circuit.width - 4)
    compute = []
    product_index = 4
    for layer in range(depth):
        matrix = circuit.state_transform_matrices[layer].data
        wires = circuit.CNOT_layers_qubits[layer]
        operations = matrix_gates(matrix, wires)
        compute.extend(operations)
        # Use the actual reconstructed gates to propagate symbolic wire states.
        execute(operations, masks)
        for slot, target in enumerate(circuit.Toffoli_layers_qubits[layer]):
            left, right = wires[2 * slot: 2 * slot + 2]
            if masks[target] or len({left, right, target}) != 3:
                raise AssertionError("Invalid temporary-AND allocation")
            compute.append(("and", left, right, target))
            masks[target] = 1 << product_index
            product_index += 1

    # Append independent output wires. Copy from the transformed basis before
    # uncomputing the products, so y may initially hold an arbitrary nibble.
    sources = output_cnot_sources(masks)
    output = []
    for index, expression in enumerate(layers[-1]):
        mask, constant = affine_mask(expression)
        target = circuit.width + index
        output.extend(("cx", wire, target) for wire in sources[mask])
        if constant:
            output.append(("x", target))
    return CleanSbox(circuit.width + 4, compute + output + undo(compute))


def put_hex(state, wires, value):
    bits = [int(char, 16) >> i & 1 for char in value for i in range(4)]
    if len(wires) != len(bits):
        raise ValueError("Register length differs from supplied hex value")
    for wire, bit in zip(wires, bits):
        state[wire] = bit


def get_hex(state, wires):
    return "".join(
        f"{sum(state[w] << i for i, w in enumerate(nibble)):x}"
        for nibble in nibbles(wires)
    )


def nibbles(wires):
    return [list(wires[i:i + 4]) for i in range(0, len(wires), 4)]


def check_sboxes(forward, inverse, lut):
    inverse_lut = [lut.index(value) for value in range(16)]
    for gadget, expected in ((forward, lut), (inverse, inverse_lut)):
        for x in range(16):
            for y in range(16):
                original = [0] * gadget.width
                put_hex(original, list(range(4)), f"{x:x}")
                put_hex(original, list(range(gadget.width - 4, gadget.width)), f"{y:x}")
                expected_state = original.copy()
                put_hex(expected_state, list(range(gadget.width - 4, gadget.width)),
                        f"{y ^ expected[x]:x}")
                execute(gadget.gates, original)
                if original != expected_state:
                    raise AssertionError("Clean S-box failed on nonzero output or left garbage")


def read_mixcolumn(path):
    text = path.read_text(encoding="utf-8")
    mapping = re.search(r"physical_output_i_is_logical_output: (\[.*\])", text)
    permutation = json.loads(mapping.group(1))
    gates = [
        (int(source), int(target))
        for source, target in re.findall(r"CNOT q(\d+) -> q(\d+)", text)
    ]
    if len(gates) != 24 or sorted(permutation) != list(range(4)):
        raise ValueError("Unexpected MixColumn fixture")
    return gates, permutation


def add_key(gates, state, components):
    for component in components:
        for source, target in zip(component, state):
            gates.extend(("cx", c, t) for c, t in zip(source, target))


def update_key(gates, components, permutation):
    next_components = []
    for index, component in enumerate(components):
        updated = []
        for a, b, c, d in component:  # least-significant bit first
            if index == 1:
                gates.append(("cx", d, a))
                updated.append([b, c, d, a])
            elif index == 2:
                gates.append(("cx", c, d))
                updated.append([d, a, b, c])
            else:
                updated.append([a, b, c, d])
        next_components.append([updated[position] for position in permutation])
    return next_components


@dataclass
class Encryption:
    gates: list
    ciphertext_wires: list
    checkpoints: list
    initial_key_cnot: int


def compile_encryption(reference, variant, key_wires, state_wires, workspace,
                       forward, inverse, mixcolumn):
    params = reference.PARAMETERS[variant]
    rounds = params["rounds"]
    components = [
        nibbles(key_wires[offset:offset + 128])
        for offset in range(0, len(key_wires), 128)
    ]
    state = nibbles(state_wires)
    free = list(workspace)
    scratch_width = max(forward.width, inverse.width) - 8
    gates = []
    add_key(gates, state, components)
    initial_key_cnot = len(gates)
    checkpoints = [(len(gates), state_wires)]
    for round_number in range(rounds):
        for start in range(0, 32, 8):
            old = state[start:start + 8]
            # Reuse the inactive portion of the fixed second state bank.
            needed = 32 + 8 * scratch_width
            if len(free) < needed:
                raise AssertionError("Selected group exceeds the fixed workspace")
            output = nibbles(free[:32])
            scratch = [
                free[32 + i * scratch_width: 32 + (i + 1) * scratch_width]
                for i in range(8)
            ]
            for source, target, local in zip(old, output, scratch):
                gates.extend(forward.on_wires(source, target, local))
            for source, target, local in zip(old, output, scratch):
                gates.extend(inverse.on_wires(target, source, local))
            state[start:start + 8] = output
            free = free[32:] + [wire for nibble in old for wire in nibble]
        if round_number < rounds - 1:
            constants = [0] * 32
            reference.add_constant(constants, variant, round_number)
            for value, nibble in zip(constants, state):
                gates.extend(("x", wire) for bit, wire in enumerate(nibble) if value >> bit & 1)
            state = [state[position] for position in reference.POS]
            mix_gates, permutation = mixcolumn
            for base in range(0, 32, 4):
                column = [wire for nibble in state[base:base + 4] for wire in nibble]
                gates.extend(("cx", column[c], column[t]) for c, t in mix_gates)
                before_relabel = state[base:base + 4]
                for physical, logical in enumerate(permutation):
                    state[base + logical] = before_relabel[physical]
        components = update_key(gates, components, reference.F_BOX)
        add_key(gates, state, components)
        checkpoints.append((len(gates), [wire for nibble in state for wire in nibble]))
    return Encryption(gates, checkpoints[-1][1], checkpoints, initial_key_cnot)


def check_encryption(encryption, vector, reference, reference_witness, key_bits):
    initial = [0] * (key_bits + 256)
    put_hex(initial, range(key_bits), vector["key"])
    put_hex(initial, range(key_bits, key_bits + 128), vector["plaintext"])
    expected, trace = reference.encrypt(
        vector["plaintext"], vector["key"], vector["variant"], reference_witness
    )
    if expected != vector["ciphertext"]:
        raise AssertionError("The independent reference differs from the official vector")
    state = initial.copy()
    previous = 0
    for (offset, wires), expected_state in zip(encryption.checkpoints, trace, strict=True):
        execute(encryption.gates[previous:offset], state)
        if get_hex(state, wires) != expected_state:
            raise AssertionError(f"{vector['variant']}: round checkpoint mismatch at gate {offset}")
        inactive = set(range(key_bits, key_bits + 256)) - set(wires)
        if any(state[wire] for wire in inactive):
            raise AssertionError(f"{vector['variant']}: inactive state workspace is not zero")
        previous = offset
    execute(undo(encryption.gates), state)
    if state != initial:
        raise AssertionError(f"{vector['variant']}: inverse replay did not restore all wires")


def load_plaintext_gates(plaintext, wires):
    prepared = [0] * len(wires)
    put_hex(prepared, range(len(wires)), plaintext)
    return [("x", wire) for value, wire in zip(prepared, wires) if value]


def compile_joint_flag(ciphertext_wires, targets, tree_wires, flag):
    gates = []
    controls = []
    for wires, target in zip(ciphertext_wires, targets, strict=True):
        gates.extend(load_plaintext_gates(f"{int(target, 16) ^ ((1 << 128) - 1):032x}", wires))
        controls.extend(wires)
    tree = iter(tree_wires)
    while len(controls) > 1:
        next_controls = []
        for index in range(0, len(controls) - 1, 2):
            target = next(tree)
            gates.append(("and", controls[index], controls[index + 1], target))
            next_controls.append(target)
        if len(controls) % 2:
            next_controls.append(controls[-1])
        controls = next_controls
    return gates + [("cx", controls[0], flag)]


def check_oracle(reference, model, variant, vector, reference_witness, compile_cipher):
    key_bits = model["key_bits"]
    count = model["pairs"]
    keys = [list(range(j * key_bits, (j + 1) * key_bits)) for j in range(count)]
    offset = count * key_bits
    banks = [list(range(offset + 256 * j, offset + 256 * (j + 1))) for j in range(count)]
    tree = list(range(offset + 256 * count, offset + 384 * count - 1))
    fixed_width = offset + 384 * count - 1
    inputs = [vector["plaintext"]] + [f"{j:032x}" for j in range(count - 1)]
    targets = [vector["ciphertext"]] + [
        reference.encrypt(pt, vector["key"], variant, reference_witness)[0]
        for pt in inputs[1:]
    ]
    compute = [
        ("cx", source, target) for copy in keys[1:]
        for source, target in zip(keys[0], copy)
    ]
    ciphertext_wires = []
    for key, bank, pt in zip(keys, banks, inputs, strict=True):
        compute.extend(load_plaintext_gates(pt, bank[:128]))
        cipher = compile_cipher(variant, key, bank[:128], bank[128:])
        compute.extend(cipher.gates)
        ciphertext_wires.append(cipher.ciphertext_wires)
    flag = min(set(banks[0]) - set(ciphertext_wires[0]))
    initial = [0] * fixed_width
    put_hex(initial, keys[0], vector["key"])
    ciphertext_state = initial.copy()
    execute(compute, ciphertext_state)
    if [get_hex(ciphertext_state, wires) for wires in ciphertext_wires] != targets:
        raise AssertionError(f"{variant}: incorrect ciphertext in the pair-parallel tape")
    cases = [targets]
    for i in range(count):
        changed = targets.copy()
        changed[i] = f"{int(changed[i], 16) ^ 1:032x}"
        cases.append(changed)
    for i, expected in enumerate(cases):
        state = ciphertext_state.copy()
        compare = compile_joint_flag(ciphertext_wires, expected, tree, flag)
        execute(compare, state)
        match = i == 0
        if state[flag] != int(match):
            raise AssertionError(f"{variant}: incorrect oracle flag in case {i}")
        sign = execute([("z", flag)], state)
        sign = execute(undo(compare), state, sign)
        if state != ciphertext_state:
            raise AssertionError(f"{variant}: comparator did not clear")
        sign = execute(undo(compute), state, sign)
        if sign != (-1 if match else 1) or state != initial:
            raise AssertionError(f"{variant}: oracle did not preserve phase and restore all wires")
    return fixed_width, len(cases)


def read_model(root):
    return json.loads((root / "data" / "resource_model.json").read_text(encoding="utf-8"))


def verify(root):
    reference = load_reference(root)
    sys.path[:0] = [str(root / "src" / "mapping"), str(root / "src")]
    mapper = import_module("classical_to_quantum")
    parser = import_module("linear_parser")
    forward = clean_sbox(root / "data/netlists/forward/ulbc.netlist", mapper, parser)
    inverse = clean_sbox(root / "data/netlists/inverse/ulbc_inverse.netlist", mapper, parser)
    check_sboxes(forward, inverse, reference.SBOX)
    mixcolumn = read_mixcolumn(root / "frozen_results/mixcolumn/mixcolumn_24cnot_depth5.netlist")
    model = read_model(root)
    reference_witness = json.loads(reference.WITNESS.read_text(encoding="utf-8"))["gate_list"]
    vectors = json.loads(reference.KAT.read_text(encoding="utf-8"))["vectors"]

    def compile_cipher(variant, key, state, workspace):
        return compile_encryption(reference, variant, key, state, workspace, forward, inverse, mixcolumn)

    results = []
    for variant, params in model["variants"].items():
        key_bits = params["key_bits"]
        encryption = compile_cipher(variant, list(range(key_bits)),
                                    list(range(key_bits, key_bits + 128)),
                                    list(range(key_bits + 128, key_bits + 256)))
        official = [vector for vector in vectors if vector["variant"] == variant]
        for vector in official:
            check_encryption(encryption, vector, reference, reference_witness, key_bits)
        width, restores = check_oracle(reference, params, variant, official[0],
                                       reference_witness, compile_cipher)
        results.append({
            "variant": variant,
            "rounds": params["rounds"],
            "full_round_kat_and_inverse_passed": len(official),
            "round_checkpoints_passed": len(official) * len(encryption.checkpoints),
            "oracle_pairs": params["pairs"],
            "all_match_passed": 1,
            "single_pair_mismatch_passed": params["pairs"],
            "ideal_phase_and_workspace_restoration_passed": restores,
            "encryption_workspace_budget": key_bits + 256,
            "oracle_workspace_budget": width,
            "encryption_tape_sha256": hashlib.sha256(
                json.dumps(encryption.gates, separators=(",", ":")).encode()
            ).hexdigest(),
        })
    return {
        "scope": "Basis-state functional verification of the reconstructed logical gate sequence; ideal temporary-AND erasure and phase sign.",
        "resource_scope": "Functional checks only; tabulated resource budgets are evaluated separately by the declared resource model.",
        "sbox_clean_interface_pass_per_map": 256,
        "official_vectors_passed": sum(row["full_round_kat_and_inverse_passed"] for row in results),
        "round_checkpoints_passed": sum(row["round_checkpoints_passed"] for row in results),
        "oracle_cases_passed": sum(row["ideal_phase_and_workspace_restoration_passed"] for row in results),
        "results": results,
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("artifact_root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    cli.add_argument("--check-record", action="store_true", help="compare functional results with the R2 validation record")
    cli.add_argument("--output-json", type=Path, help="write a separate output file")
    args = cli.parse_args()
    root = args.artifact_root.resolve()
    result = verify(root)
    if args.check_record:
        record = json.loads((root / "results/r2/ulbc_gate_checks.json").read_text(encoding="utf-8"))
        if result != record:
            raise AssertionError("functional results differ from the R2 validation record")
    payload = json.dumps(result, indent=2) + "\n"
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
