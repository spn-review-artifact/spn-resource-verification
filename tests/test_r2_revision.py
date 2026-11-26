from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))

import verify_r2_ulbc_gate_sequence as functional
import verify_table14 as table14


class R2RevisionTests(unittest.TestCase):
    def test_full_round_and_multi_pair_functional_checks(self):
        with redirect_stdout(io.StringIO()):
            result = functional.verify(ROOT)
        expected = json.loads((ROOT/'results/r2/ulbc_gate_checks.json').read_text(encoding='utf-8'))
        self.assertEqual(result, expected)
        self.assertEqual((result['official_vectors_passed'], result['round_checkpoints_passed'], result['oracle_cases_passed']), (6, 146, 12))
        self.assertEqual([row['oracle_pairs'] for row in result['results']], [2, 3, 4])

    def test_table14_matches_manuscript_conversion_record(self):
        result = table14.verify(ROOT)
        expected = json.loads((ROOT/'results/r2/table14_check.json').read_text(encoding='utf-8'))
        self.assertEqual(result, expected)
        rows = {row['sbox']: row for row in result['rows']}
        self.assertEqual(len(rows), 8)
        # The manuscript uses seed 0, not the lowest CNOT value across seeds.
        self.assertEqual(rows['RECTANGLE']['qusat']['cnot_outside_qand'], 62)
        self.assertEqual(rows['KLEIN']['qusat']['cnot_outside_qand'], 87)
        self.assertEqual(rows['uLBC']['qusat']['cnot_estimate_4t'], 77)
        # A native CNOT count and the clean lowered estimate are distinct.
        self.assertEqual(rows['SKINNY']['lighter_r_wrapper']['native_counts']['CNOT'], 0)
        self.assertEqual(rows['SKINNY']['lighter_r_wrapper']['cnot_estimate_4t'], 84)

    def test_gift_minimum_status_uses_conclusive_retry(self):
        catalog = json.loads((ROOT/'data/reference/sboxes.json').read_text(encoding='utf-8'))['sboxes']
        retry = json.loads((ROOT/'data/solver/retry_300s_seed1.json').read_text(encoding='utf-8'))
        call = next(row for row in retry['attempts'] if row['cipher'] == 'GIFT')
        self.assertEqual((call['total_k'], call['k1'], call['k2'], call['solver_status']), (4, 2, 2, 'unsat'))
        self.assertEqual(catalog['GIFT']['minimum_status'], 'minimum-proved-within-bounded-AND-depth-2-space')
        self.assertEqual(catalog['PRINCE']['minimum_status'], 'verified-best-found-lower-instance-unknown')

    def test_original_extended_netlist_coverage_is_explicit(self):
        result = table14.verify(ROOT)
        record_only = result['record_only_extended_rows']
        if record_only:
            with self.assertRaisesRegex(AssertionError, 'Gate-file coverage unavailable'):
                table14.verify(ROOT, require_all_witnesses=True)
        else:
            self.assertEqual(table14.verify(ROOT, require_all_witnesses=True), result)


if __name__ == '__main__':
    unittest.main()
