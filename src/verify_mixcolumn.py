#!/usr/bin/env python3
"""Independently reconstruct and exhaustively verify the 24-CNOT layer."""

from __future__ import annotations

from collections import deque
from itertools import permutations
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IDENTITY = (1, 2, 4, 8)
TARGET = (0b1110, 0b1101, 0b1011, 0b0111)


def apply_cnot(matrix: tuple[int, ...], source: int, target: int) -> tuple[int, ...]:
    rows = list(matrix)
    rows[target] ^= rows[source]
    return tuple(rows)


def asap_layers(gates: list[tuple[int, int]]) -> list[int]:
    available = [0] * 4
    layers = []
    for source, target in gates:
        layer = max(available[source], available[target]) + 1
        available[source] = layer
        available[target] = layer
        layers.append(layer)
    return layers


def shortest_relabelled_circuit() -> tuple[list[tuple[int, int]], list[int], tuple[int, ...]]:
    targets = {
        tuple(TARGET[index] for index in permutation): permutation
        for permutation in permutations(range(4))
    }
    queue = deque([IDENTITY])
    previous: dict[tuple[int, ...], tuple[int, ...] | None] = {IDENTITY: None}
    incoming: dict[tuple[int, ...], tuple[int, int]] = {}
    distance = {IDENTITY: 0}
    found_distance = None
    found = []
    while queue:
        state = queue.popleft()
        current = distance[state]
        if state in targets:
            if found_distance is None:
                found_distance = current
            if current == found_distance:
                found.append(state)
        for source in range(4):
            for target in range(4):
                if source == target:
                    continue
                successor = apply_cnot(state, source, target)
                if successor not in previous:
                    previous[successor] = state
                    incoming[successor] = (source, target)
                    distance[successor] = current + 1
                    queue.append(successor)
    candidates = []
    for state in found:
        gates = []
        cursor = state
        while previous[cursor] is not None:
            gates.append(incoming[cursor])
            cursor = previous[cursor]  # type: ignore[assignment]
        gates.reverse()
        layers = asap_layers(gates)
        candidates.append((max(layers), gates, layers, targets[state]))
    depth, gates, layers, permutation = min(candidates)
    assert len(previous) == 20160
    assert len(gates) == 6 and depth == 5
    return gates, layers, permutation


def mix_nibbles(value: int) -> int:
    nibbles = [(value >> (4 * index)) & 0xF for index in range(4)]
    outputs = [
        nibbles[(row + 1) % 4] ^ nibbles[(row + 2) % 4] ^ nibbles[(row + 3) % 4]
        for row in range(4)
    ]
    return sum(item << (4 * index) for index, item in enumerate(outputs))


def simulate(value: int, gates: list[tuple[int, int]], permutation: tuple[int, ...]) -> int:
    physical = [(value >> (4 * index)) & 0xF for index in range(4)]
    for source, target in gates:
        physical[target] ^= physical[source]
    logical = [0] * 4
    for physical_index, logical_index in enumerate(permutation):
        logical[logical_index] = physical[physical_index]
    return sum(item << (4 * index) for index, item in enumerate(logical))


def verify() -> dict[str, object]:
    gates, layers, permutation = shortest_relabelled_circuit()
    passed = sum(
        simulate(value, gates, permutation) == mix_nibbles(value)
        for value in range(1 << 16)
    )
    result = {
        "search_space": "all 20160 matrices in GL(4,2)",
        "free_operation": "final output-wire relabeling",
        "bit_slice_cnot_count": len(gates),
        "column_cnot_count": 4 * len(gates),
        "column_physical_asap_depth": max(layers),
        "output_permutation_physical_to_logical": list(permutation),
        "verification": f"pass-{passed}/{1 << 16}",
    }
    frozen = json.loads(
        (ROOT / "frozen_results" / "mixcolumn" / "mixcolumn_verification.json").read_text(
            encoding="utf-8"
        )
    )
    for key in (
        "bit_slice_cnot_count",
        "column_cnot_count",
        "column_physical_asap_depth",
        "output_permutation_physical_to_logical",
        "verification",
    ):
        if result[key] != frozen[key]:
            raise AssertionError(f"frozen mismatch for {key}: {result[key]} != {frozen[key]}")
    print(json.dumps(result, indent=2))
    return result


def main() -> int:
    verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
