#!/usr/bin/env python3
"""Verify the released in-place S-box witness in complete uLBC instances.

The implementation follows the public VHDL bit/nibble order and checks all six
published testbench vectors.  Encryption uses the synthesized in-place gate
list rather than a lookup table.  The inverse run reverses the same witness and
round operations, proving state-register overwrite and restoration across all
rounds for these complete cipher instances.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WITNESS = ROOT / "data" / "witnesses" / "ulbc_inplace_k4.json"
KAT = ROOT / "data" / "reference" / "ulbc_kat.json"
FROZEN = ROOT / "frozen_results" / "ulbc_multiround" / "ulbc_multiround_verification.json"

SBOX = [int(char, 16) for char in "8015C7462A3DEFB9"]
POS = [
    0, 25, 18, 15, 4, 1, 30, 19, 8, 29, 22, 7, 12, 9, 26, 23,
    20, 5, 10, 31, 16, 13, 2, 27, 28, 17, 6, 3, 24, 21, 14, 11,
]
POS_INV = [
    0, 5, 22, 27, 4, 17, 26, 11, 8, 13, 18, 31, 12, 21, 30, 3,
    20, 25, 2, 7, 16, 29, 10, 15, 28, 1, 14, 23, 24, 9, 6, 19,
]
F_BOX = [
    8, 24, 28, 23, 9, 31, 14, 17, 20, 19, 26, 5, 18, 2, 6, 30,
    4, 15, 11, 25, 10, 29, 12, 3, 21, 16, 7, 0, 27, 13, 22, 1,
]
F1 = [0, 8, 1, 9, 2, 10, 3, 11, 12, 4, 13, 5, 14, 6, 15, 7]
F2 = [0, 2, 4, 6, 9, 11, 13, 15, 1, 3, 5, 7, 8, 10, 12, 14]
RC0 = [
    0x8, 0xC, 0xE, 0xF, 0xF, 0x7, 0xB, 0xD, 0xE, 0xF, 0x7, 0x3, 0x9, 0xC, 0xE, 0x7,
    0xB, 0x5, 0xA, 0xD, 0x6, 0x3, 0x1, 0xC, 0x8, 0x4, 0xA, 0xD, 0xE, 0x7, 0x3, 0x1,
]
RC1 = [
    0x0, 0x0, 0x0, 0x0, 0x8, 0xC, 0xC, 0xC, 0xC, 0x4, 0x8, 0xC, 0xC, 0xC, 0x4, 0x0,
    0x8, 0xC, 0xC, 0x4, 0x8, 0x4, 0x8, 0x0, 0x4, 0x0, 0x0, 0x0, 0x8, 0x4, 0x8, 0xC,
]
RC6 = [
    0xA, 0xA, 0x9, 0x2, 0xA, 0x4, 0xC, 0x9, 0xC, 0x3, 0x3, 0x1, 0xC, 0x9, 0xC, 0x8,
    0x4, 0x2, 0xC, 0x8, 0x4, 0xC, 0x9, 0xA, 0x8, 0xC, 0x0, 0xB, 0x4, 0x2, 0xC, 0x1,
]
RC7 = [
    0x0, 0xC, 0x3, 0x9, 0xC, 0xB, 0x9, 0x1, 0x2, 0x1, 0x2, 0x9, 0x1, 0x3, 0xA, 0x1,
    0x4, 0x0, 0xB, 0xB, 0x9, 0xC, 0xB, 0x8, 0x2, 0x1, 0x4, 0xA, 0xA, 0x2, 0x9, 0x8,
]
PARAMETERS = {
    "uLBC-128": {"rounds": 18, "components": 1, "middle": [0xC, 0x5, 0xC, 0x5]},
    "uLBC-256": {"rounds": 22, "components": 2, "middle": [0x3, 0xC, 0x3, 0xC]},
    "uLBC-384t": {"rounds": 30, "components": 3, "middle": [0x5, 0xA, 0x5, 0xA]},
}


def apply_gate(value: int, gate: list[object]) -> int:
    name = str(gate[0])
    operands = [int(item) for item in gate[1:]]
    if name == "X":
        return value ^ (1 << operands[0])
    if name == "CNOT":
        control, target = operands
        return value ^ (((value >> control) & 1) << target)
    if name == "TOFFOLI":
        first, second, target = operands
        return value ^ ((((value >> first) & 1) & ((value >> second) & 1)) << target)
    if name == "SWAP":
        first, second = operands
        delta = ((value >> first) ^ (value >> second)) & 1
        return value ^ (delta << first) ^ (delta << second)
    raise ValueError(name)


def apply_sbox(value: int, gates: list[list[object]], inverse: bool = False) -> int:
    sequence = reversed(gates) if inverse else gates
    for gate in sequence:
        value = apply_gate(value, gate)
    return value


def nibbles(text: str) -> list[int]:
    return [int(char, 16) for char in text.lower()]


def hex_state(state: list[int]) -> str:
    return "".join(format(value, "x") for value in state)


def update_components(components: list[list[int]]) -> list[list[int]]:
    transforms = [None, F1, F2]
    result = []
    for component_index, component in enumerate(components):
        transform = transforms[component_index]
        prepared = component if transform is None else [transform[value] for value in component]
        result.append([prepared[F_BOX[index]] for index in range(32)])
    return result


def round_keys(key_hex: str, component_count: int, rounds: int) -> list[list[int]]:
    key = nibbles(key_hex)
    components = [key[index * 32 : (index + 1) * 32] for index in range(component_count)]
    keys = [[0] * 32 for _ in range(rounds + 1)]
    for index in range(32):
        keys[0][index] = 0
        for component in components:
            keys[0][index] ^= component[index]
    for round_index in range(1, rounds + 1):
        components = update_components(components)
        for index in range(32):
            for component in components:
                keys[round_index][index] ^= component[index]
    return keys


def mixcolumn(state: list[int]) -> list[int]:
    result = [0] * 32
    for column in range(8):
        offset = 4 * column
        values = state[offset : offset + 4]
        for row in range(4):
            result[offset + row] = values[(row + 1) % 4] ^ values[(row + 2) % 4] ^ values[(row + 3) % 4]
    return result


def add_constant(state: list[int], variant: str, round_index: int) -> None:
    middle = PARAMETERS[variant]["middle"]
    constants = [RC0[round_index], RC1[round_index], *middle, RC6[round_index], RC7[round_index]]
    for index, value in enumerate(constants):
        state[index] ^= value


def xor_key(state: list[int], key: list[int]) -> list[int]:
    return [left ^ right for left, right in zip(state, key)]


def encrypt(
    plaintext: str, key_hex: str, variant: str, gates: list[list[object]]
) -> tuple[str, list[str]]:
    rounds = int(PARAMETERS[variant]["rounds"])
    components = int(PARAMETERS[variant]["components"])
    keys = round_keys(key_hex, components, rounds)
    state = xor_key(nibbles(plaintext), keys[0])
    trace = [hex_state(state)]
    for round_number in range(1, rounds):
        state = [apply_sbox(value, gates) for value in state]
        add_constant(state, variant, round_number - 1)
        state = [state[POS[index]] for index in range(32)]
        state = mixcolumn(state)
        state = xor_key(state, keys[round_number])
        trace.append(hex_state(state))
    state = [apply_sbox(value, gates) for value in state]
    state = xor_key(state, keys[rounds])
    trace.append(hex_state(state))
    return hex_state(state), trace


def decrypt(
    ciphertext: str, key_hex: str, variant: str, gates: list[list[object]]
) -> str:
    rounds = int(PARAMETERS[variant]["rounds"])
    components = int(PARAMETERS[variant]["components"])
    keys = round_keys(key_hex, components, rounds)
    state = xor_key(nibbles(ciphertext), keys[rounds])
    state = [apply_sbox(value, gates, inverse=True) for value in state]
    for round_number in range(rounds - 1, 0, -1):
        state = xor_key(state, keys[round_number])
        state = mixcolumn(state)  # involution
        state = [state[POS_INV[index]] for index in range(32)]
        add_constant(state, variant, round_number - 1)
        state = [apply_sbox(value, gates, inverse=True) for value in state]
    state = xor_key(state, keys[0])
    return hex_state(state)


def main() -> int:
    witness = json.loads(WITNESS.read_text(encoding="utf-8"))
    gates = witness["gate_list"]
    if [apply_sbox(value, gates) for value in range(16)] != SBOX:
        raise RuntimeError("in-place witness does not match the uLBC S-box")
    kat = json.loads(KAT.read_text(encoding="utf-8"))
    rows = []
    for vector in kat["vectors"]:
        calculated, trace = encrypt(
            vector["plaintext"], vector["key"], vector["variant"], gates
        )
        recovered = decrypt(calculated, vector["key"], vector["variant"], gates)
        rows.append(
            {
                **vector,
                "calculated_ciphertext": calculated,
                "encryption_check": "pass" if calculated == vector["ciphertext"] else "fail",
                "recovered_plaintext": recovered,
                "inverse_check": "pass" if recovered == vector["plaintext"] else "fail",
                "round_trace_sha256": hashlib.sha256(
                    "\n".join(trace).encode("ascii")
                ).hexdigest(),
                "states_in_trace": len(trace),
            }
        )
    if not all(
        row["encryption_check"] == "pass" and row["inverse_check"] == "pass"
        for row in rows
    ):
        raise RuntimeError(json.dumps(rows, indent=2))
    payload = {
        "witness": str(WITNESS.relative_to(ROOT)),
        "kat_source": str(KAT.relative_to(ROOT)),
        "sbox_truth_table": "pass-16/16",
        "test_vectors": rows,
        "summary": "pass-6/6 encryption and pass-6/6 inverse restoration",
        "register_reuse_conclusion": (
            "The same 128-bit state is overwritten by the verified in-place S-box in every "
            "round and is restored by reversing the complete cipher computation."
        ),
    }
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    frozen_rows = {
        (row["variant"], row["plaintext"], row["key"]): row
        for row in frozen["test_vectors"]
    }
    for row in rows:
        expected = frozen_rows[(row["variant"], row["plaintext"], row["key"])]
        for field in (
            "ciphertext",
            "calculated_ciphertext",
            "encryption_check",
            "recovered_plaintext",
            "inverse_check",
            "round_trace_sha256",
            "states_in_trace",
        ):
            if row[field] != expected[field]:
                raise AssertionError(
                    f"frozen mismatch for {row['variant']} {field}: "
                    f"{row[field]} != {expected[field]}"
                )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
