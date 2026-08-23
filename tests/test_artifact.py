from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import recompute_resource_tables as resources  # noqa: E402
import check_fixed_smt2 as fixed_smt  # noqa: E402
import reference_smt_encoder as reference_encoder  # noqa: E402
import verify_external_validation as external  # noqa: E402
import verify_mixcolumn as mixcolumn  # noqa: E402
import verify_sbox_witnesses as sboxes  # noqa: E402
import verify_table10_models as table10  # noqa: E402


class SboxEvidenceTests(unittest.TestCase):
    def test_all_primary_fixed_smt_instances(self) -> None:
        rows = fixed_smt.check_all()
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(row["observed_status"] == "sat" for row in rows))
        self.assertTrue(
            all(row["claim_scope"] == "feasibility-only-not-minimality" for row in rows)
        )

    def test_public_encoder_matches_all_frozen_constraint_sets(self) -> None:
        metadata = json.loads(
            (ROOT / "data" / "solver" / "fixed_instances.json").read_text(
                encoding="utf-8"
            )
        )
        for record in metadata["instances"]:
            target = reference_encoder.parse_lut(record["target_lut"])
            solver, _ = reference_encoder.build_fixed_solver(
                target, record["k1"], record["k2"]
            )
            frozen = (ROOT / record["file"]).read_text(encoding="utf-8")
            self.assertIn(solver.sexpr(), frozen, record["cipher"])

    def test_public_encoder_exports_verified_sat_witness(self) -> None:
        target = reference_encoder.parse_lut("8015C7462A3DEFB9")
        row, _, operations = reference_encoder.run_fixed(
            "uLBC", target, k1=1, k2=3, timeout_ms=60_000, seed=0
        )
        self.assertEqual(row["solver_status"], "sat")
        self.assertEqual(row["truth_table_check"], "pass-16/16")
        self.assertIsNotNone(operations)
        self.assertTrue(reference_encoder.verify_netlist(operations or [], target))

    def test_public_bounded_search_handles_affine_zero_and_case(self) -> None:
        target = reference_encoder.parse_lut("0123456789ABCDEF")
        result, _, operations, shape = reference_encoder.bounded_search(
            "identity", target, k_min=0, k_max=0, timeout_ms=10_000, seed=0
        )
        self.assertEqual(result["first_sat_total_k"], 0)
        self.assertEqual(shape, (0, 0))
        self.assertTrue(reference_encoder.verify_netlist(operations or [], target))

    def test_released_forward_and_inverse_witnesses(self) -> None:
        rows = sboxes.verify_all()
        self.assertEqual(len(rows), 6)
        self.assertTrue(
            all(row["forward"]["truth_table_check"] == "pass-16/16" for row in rows)
        )
        self.assertTrue(
            all(row["inverse"]["truth_table_check"] == "pass-16/16" for row in rows)
        )
        self.assertTrue(
            all(row["reuse_safe_transition_check"] == "pass-16/16" for row in rows)
        )

    def test_timeout_is_not_an_unsat_proof(self) -> None:
        retry = json.loads(
            (ROOT / "data" / "solver" / "retry_600s_seed2.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(
            all(item["conclusion"] == "still-unresolved" for item in retry["summaries"])
        )
        self.assertTrue(
            all(item["solver_status"] == "unknown" for item in retry["attempts"])
        )


class ResourceEvidenceTests(unittest.TestCase):
    def test_recomputed_rows_match_frozen_files(self) -> None:
        model = json.loads(
            (ROOT / "data" / "resource_model.json").read_text(encoding="utf-8")
        )
        encryption = resources.build_encryption_rows(model)
        complete = resources.build_complete_rows(model, encryption)
        resources.check_frozen(encryption, complete)

    def test_schedule_tradeoff(self) -> None:
        model = json.loads(
            (ROOT / "data" / "resource_model.json").read_text(encoding="utf-8")
        )
        rows = {
            (row["variant"], row["sbox_schedule"]): row
            for row in resources.build_encryption_rows(model)
        }
        parallel = rows[("uLBC-128", "fully-parallel")]
        four = rows[("uLBC-128", "four-group")]
        serial = rows[("uLBC-128", "fully-serial")]
        self.assertEqual(parallel["t_count"], four["t_count"])
        self.assertEqual(four["t_count"], serial["t_count"])
        self.assertLess(parallel["t_depth"], four["t_depth"])
        self.assertLess(four["t_depth"], serial["t_depth"])
        self.assertGreater(parallel["tight_peak_width"], four["tight_peak_width"])
        self.assertGreater(four["tight_peak_width"], serial["tight_peak_width"])

    def test_pair_schedule_consistency_and_standard_costs(self) -> None:
        model = json.loads(
            (ROOT / "data" / "resource_model.json").read_text(encoding="utf-8")
        )
        encryption = resources.build_encryption_rows(model)
        rows = resources.build_complete_rows(model, encryption)
        selected = {
            (row["variant"], row["schedule"]): row
            for row in rows
            if row["sbox_schedule"] == "four-group"
        }
        parallel = selected[("uLBC-256", "pair-parallel")]
        serial = selected[("uLBC-256", "pair-serial")]
        self.assertGreater(parallel["iteration_width"], serial["iteration_width"])
        self.assertLess(parallel["iteration_full_depth_bound"], serial["iteration_full_depth_bound"])
        self.assertNotEqual(parallel["log2_full_search_g_upper"], parallel["log2_full_search_dw"])
        self.assertIn("comparator_t_count", parallel)
        self.assertIn("diffusion_t_count", parallel)

    def test_mixcolumn(self) -> None:
        result = mixcolumn.verify()
        self.assertEqual(result["verification"], "pass-65536/65536")


class ExternalEvidenceTests(unittest.TestCase):
    def test_external_records(self) -> None:
        result = external.verify()
        self.assertEqual(result["primary_sboxes"], 6)
        self.assertEqual(result["extended_qusat_seed_runs"], 12)

    def test_table10_models(self) -> None:
        rows = table10.verify()
        unitary = [row for row in rows if row["t_model"] == "unitary-matrix-decomposition"]
        self.assertEqual(len(unitary), 2)
        self.assertTrue(
            all(row["comparison_status"] == "non-normalizable-context" for row in unitary)
        )

    def test_no_twine_row_in_released_extended_table(self) -> None:
        for filename in ("lighter_r_extended.csv", "qusat_extended.csv"):
            with (ROOT / "data" / "external" / filename).open(
                newline="", encoding="utf-8"
            ) as handle:
                names = {row["target"] for row in csv.DictReader(handle)}
            self.assertNotIn("TWINE", names)


if __name__ == "__main__":
    unittest.main()
