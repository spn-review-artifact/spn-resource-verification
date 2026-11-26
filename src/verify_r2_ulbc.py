"""Check R2 uLBC witnesses against official vectors and joint matching cases.

Usage: python verify_r2_ulbc.py PATH_TO_SPN_RESOURCE_VERIFICATION
This is a Boolean block-level check, including the clean state transition.
"""

import argparse
import importlib.util
import json
from pathlib import Path


def load_reference(root):
    path = root / "src" / "verify_ulbc_multiround.py"
    spec = importlib.util.spec_from_file_location("ulbc_reference", path)
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    return reference


def truth_table(path):
    assignments = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        target, expression = line.split("=")
        assignments.append((target, expression.replace("+", "^")))
    table = []
    for value in range(16):
        wires = {"1": 1, "0": 0}
        wires.update({f"X{bit}": (value >> bit) & 1 for bit in range(4)})
        for target, expression in assignments:
            if "*" in expression:
                left, right = expression.split("*")
                wires[target] = wires[left] & wires[right]
            elif "^" in expression:
                left, right = expression.split("^")
                wires[target] = wires[left] ^ wires[right]
            else:
                wires[target] = wires[expression]
        table.append(sum(wires[f"Y{bit}"] << bit for bit in range(4)))
    return table


def main(root):
    reference = load_reference(root)
    reference.main()
    reference_sbox = reference.apply_sbox
    official = json.loads(reference.KAT.read_text(encoding="utf-8"))["vectors"]
    gates = json.loads(reference.WITNESS.read_text(encoding="utf-8"))["gate_list"]
    forward = truth_table(root / "data/netlists/forward/ulbc.netlist")
    inverse_map = truth_table(root / "data/netlists/inverse/ulbc_inverse.netlist")

    def clean_transition(value, _gates, inverse=False):
        compute, erase = (inverse_map, forward) if inverse else (forward, inverse_map)
        new_state = compute[value]
        old_state = value ^ erase[new_state]
        if old_state != 0:
            raise AssertionError("clean transition failed to erase the old state")
        return new_state

    if forward != reference.SBOX:
        raise AssertionError("forward netlist differs from the reference S-box")
    for value in range(16):
        clean_transition(value, None)
        clean_transition(value, None, inverse=True)

    results = []
    for variant, pair_count in (("uLBC-128", 2), ("uLBC-256", 3), ("uLBC-384t", 4)):
        vectors = [vector for vector in official if vector["variant"] == variant]
        reference.apply_sbox = clean_transition
        for vector in vectors:
            key, pt, ct = (vector[field] for field in ("key", "plaintext", "ciphertext"))
            if reference.encrypt(pt, key, variant, None)[0] != ct:
                raise AssertionError(f"{variant}: official ciphertext mismatch")
            if reference.decrypt(ct, key, variant, None) != pt:
                raise AssertionError(f"{variant}: inverse restoration mismatch")

        # Keep one official pair and derive the remaining targets with
        # the separate in-place witness under the same key.
        anchor = vectors[0]
        key = anchor["key"]
        plaintexts = [anchor["plaintext"]] + [f"{j:032x}" for j in range(pair_count - 1)]
        reference.apply_sbox = reference_sbox
        targets = [anchor["ciphertext"]] + [
            reference.encrypt(pt, key, variant, gates)[0] for pt in plaintexts[1:]
        ]
        reference.apply_sbox = clean_transition
        candidates = [targets.copy()]
        for index in range(pair_count):
            changed = targets.copy()
            changed[index] = f"{int(changed[index], 16) ^ 1:032x}"
            candidates.append(changed)
        for index, expected in enumerate(candidates):
            computed = [reference.encrypt(pt, key, variant, None)[0] for pt in plaintexts]
            matches = [value == target for value, target in zip(computed, expected)]
            if all(matches) != (index == 0):
                raise AssertionError(f"{variant}: joint predicate mismatch at case {index}")
            restored = [
                reference.decrypt(value, key, variant, None) for value in computed
            ]
            if restored != plaintexts:
                raise AssertionError(f"{variant}: pair restoration mismatch")
        results.append(
            {
                "variant": variant,
                "rounds": reference.PARAMETERS[variant]["rounds"],
                "official_vectors_passed": len(vectors),
                "pairs": pair_count,
                "all_match_passed": 1,
                "single_pair_mismatch_passed": pair_count,
                "pair_batches_restored": len(candidates),
            }
        )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_root", type=Path)
    main(parser.parse_args().artifact_root.resolve())
