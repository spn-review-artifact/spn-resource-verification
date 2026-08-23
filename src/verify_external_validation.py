#!/usr/bin/env python3
"""Check sanitized external-validation records and wrapper arithmetic."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def verify() -> dict[str, int]:
    catalog = json.loads(
        (ROOT / "data" / "reference" / "sboxes.json").read_text(encoding="utf-8")
    )["sboxes"]
    lighter = {
        row["target"].replace("SKINNY-64", "SKINNY").replace("Midori64", "Midori"): row
        for row in read_csv(ROOT / "data" / "external" / "lighter_r_primary.csv")
    }
    validation = read_csv(ROOT / "data" / "external" / "external_validation.csv")
    for row in validation:
        name = row["sbox"]
        expected = catalog[name]
        assert int(row["qusat_clean_t_count_4t"]) == 4 * int(expected["reported_k"])
        assert int(row["qusat_clean_t_depth"]) == int(expected["reported_and_depth"])
        external = lighter[name]
        assert external["verification"] == "pass-16/16"
        assert int(external["t7"]) == 7 * int(external["CCNOT"])
        # Clean wrapper U;copy;U^-1 doubles the in-place CCNOT count.  Under
        # the released temporary-AND convention each compute/uncompute pair is
        # charged 4 T, producing 8 T per in-place CCNOT occurrence.
        assert int(row["lighter_r_clean_t_count_4t"]) == 8 * int(external["CCNOT"])
        assert int(row["lighter_r_clean_t_depth"]) == 2 * int(external["CCNOT"])
        if row["dorcis_published_t_depth"]:
            assert row["dorcis_status"] == "published-only"
        else:
            assert row["dorcis_status"] == "not-reported"

    extended_lighter = read_csv(ROOT / "data" / "external" / "lighter_r_extended.csv")
    extended_qusat = read_csv(ROOT / "data" / "external" / "qusat_extended.csv")
    assert {row["target"] for row in extended_lighter} == {
        "RECTANGLE", "Piccolo", "KLEIN", "PRIDE"
    }
    assert {row["target"] for row in extended_qusat} == {
        "RECTANGLE", "Piccolo", "KLEIN", "PRIDE"
    }
    assert all(row["verification"] == "pass-16/16" for row in extended_lighter)
    assert all(row["verification"] == "pass-16/16" for row in extended_qusat)
    result = {
        "primary_sboxes": len(validation),
        "lighter_primary_verified": len(lighter),
        "extended_lighter_sboxes": len(extended_lighter),
        "extended_qusat_seed_runs": len(extended_qusat),
    }
    print(json.dumps(result, indent=2))
    print("external validation records verified")
    return result


def main() -> int:
    verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
