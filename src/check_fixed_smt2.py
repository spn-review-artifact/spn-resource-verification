#!/usr/bin/env python3
"""Check all released primary fixed SMT-LIB2 feasibility instances."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import z3


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "solver" / "fixed_instances.json"


def check_all() -> list[dict[str, object]]:
    metadata = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    for record in metadata["instances"]:
        instance = ROOT / record["file"]
        payload = instance.read_bytes()
        if len(payload) != record["bytes"]:
            raise RuntimeError(f"size mismatch: {record['file']}")
        if hashlib.sha256(payload).hexdigest() != record["sha256"]:
            raise RuntimeError(f"SHA-256 mismatch: {record['file']}")
        solver = z3.Solver()
        # Parse text rather than passing the path into the native Z3 loader so
        # a checkout under a non-ASCII Windows path remains portable.
        solver.add(z3.parse_smt2_string(payload.decode("utf-8")))
        started = time.perf_counter()
        status = solver.check()
        elapsed = time.perf_counter() - started
        expected = record["expected_status"]
        print(
            f"cipher={record['cipher']} shape=k1={record['k1']},k2={record['k2']} "
            f"status={status} elapsed_seconds={elapsed:.6f}"
        )
        if str(status) != expected:
            raise RuntimeError(
                f"{record['cipher']}: expected {expected}, received {status}"
            )
        rows.append({**record, "observed_status": str(status)})
    if len(rows) != 6:
        raise RuntimeError(f"expected six primary instances, received {len(rows)}")
    return rows


def main() -> int:
    print(f"z3={z3.get_version_string()}")
    rows = check_all()
    print(f"all_fixed_instances_verified={len(rows)}/6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
