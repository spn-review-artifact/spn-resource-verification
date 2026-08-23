#!/usr/bin/env python3
"""Audit model and scope labels in the revised cross-cipher comparison."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def optional_int(value: str) -> int | None:
    return int(value) if value else None


def verify() -> list[dict[str, str]]:
    path = ROOT / "frozen_results" / "table10_main.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 23
    for row in rows:
        assert row["encryption_calls"] in {"1", "2"}
        assert row["scope"].endswith(f"-{row['encryption_calls']}E") or row["scope"] == "published-cipher-estimate"
        t4 = optional_int(row["t_count_4t"])
        t7 = optional_int(row["t_count_exact_7t"])
        tu = optional_int(row["t_count_unitary"])
        model = row["t_model"]
        status = row["comparison_status"]
        if model == "unitary-matrix-decomposition":
            assert tu is not None and t4 is None and t7 is None
            assert status == "non-normalizable-context"
        if "relative-phase-4T" in model:
            assert t4 is not None and t7 is not None
            assert 7 * t4 == 4 * t7
        if "clean-temporary-AND-4T" in model:
            assert t4 is not None and t7 is not None
            assert 7 * t4 == 2 * t7
        if row["source"] == "Bijwe et al.":
            assert model == "exact-7T" and t7 is not None
            assert status == "model-matched-at-exact-7T"
        if status == "model-matched-at-exact-7T":
            assert t7 is not None

    by_group: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_group.setdefault(row["comparison_group"], []).append(row)
    for group, members in by_group.items():
        if any(row["comparison_status"] == "model-matched-at-exact-7T" for row in members):
            calls = {row["encryption_calls"] for row in members}
            exact = {row["t_count_exact_7t"] for row in members}
            assert len(calls) == 1, f"scope mismatch in {group}"
            assert len(exact) == 1, f"exact-7T mismatch in {group}"
    print(f"verified {len(rows)} Table 10 rows")
    print("all model-matched groups agree in encryption-call scope and exact-7T T-count")
    print("unitary-decomposition rows remain non-normalizable context")
    return rows


def main() -> int:
    verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
