#!/usr/bin/env python3
"""Check Table 14 under the manuscript's common clean interface and 4T schedules.

Native counts, declared width budgets, and lowered CNOT estimates have distinct
fields. No baseline synthesis or new SMT search is performed.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import csv
import io
import json
from pathlib import Path

from verify_sbox_witnesses import inspect

ROOT = Path(__file__).resolve().parents[1]
ORDER = ['PRESENT', 'GIFT', 'Midori', 'PRINCE', 'SKINNY', 'uLBC', 'RECTANGLE', 'KLEIN']


def read_csv(path):
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def normalize(name):
    return {'SKINNY-64': 'SKINNY', 'Midori64': 'Midori'}.get(name, name)


def clean_wrapper(cnot, toffoli):
    """U; four-bit output copy; U^-1, with serial temporary-AND scratch reuse."""
    return {'width': 9, 'cnot_estimate_4t': 2*cnot + 4 + 20*toffoli,
            't_count': 8*toffoli, 'online_t_depth': 2*toffoli}


def verify(root=ROOT, require_all_witnesses=False):
    catalog = json.loads((root/'data/reference/sboxes.json').read_text(encoding='utf-8'))['sboxes']
    extended = read_csv(root/'data/external/qusat_extended.csv')
    selected = json.loads((root/'data/external/qusat_selected_seed0.json').read_text(encoding='utf-8'))
    selected = {row['target_name']: row for row in selected['results']}
    lighter_rows = read_csv(root/'data/external/lighter_r_primary.csv') + read_csv(root/'data/external/lighter_r_extended.csv')
    lighter = {normalize(row['target']): row for row in lighter_rows}
    dorcis = json.loads((root/'data/external/dorcis_selected_circuits.json').read_text(encoding='utf-8'))
    dorcis = {row['sbox']: row for row in dorcis['circuits']}
    rows = []
    record_only = []
    for name in ORDER:
        if name in catalog:
            entry = catalog[name]
            lut = [int(value, 16) for value in entry['lut']]
            with redirect_stdout(io.StringIO()):
                actual = inspect(root/entry['forward_netlist'], lut)
            assert actual['truth_table_check'] == 'pass-16/16', name
            assert actual['and_count'] == entry['reported_k'], name
            assert actual['and_depth'] == entry['reported_and_depth'], name
            assert actual['logical_cnot'] == entry['reported_logical_cnot'], name
            k, depth = entry['reported_k'], entry['reported_and_depth']
            cnot, width = entry['reported_logical_cnot'], entry['reported_width']
            evidence = 'released-witness-and-mapping-accounting'
        else:
            record = next(row for row in extended if row['target'] == name and int(row['seed']) == 0)
            original = selected[name]['best_verified']
            assert selected[name]['seed'] == 0
            assert record['verification'] == original['verification'] == 'pass-16/16'
            k, depth = int(record['k']), int(record['t_depth'])
            cnot, width = int(record['cnot']), int(record['width'])
            assert (k, cnot, width) == (original['total_k'], original['xor_network_cnot'], original['clean_width'])
            netlist = root/f'data/netlists/extended/{name.lower()}_seed0.netlist'
            if netlist.is_file():
                with redirect_stdout(io.StringIO()):
                    actual = inspect(netlist, [int(x, 16) for x in record['lut']])
                assert actual['truth_table_check'] == 'pass-16/16', name
                assert (actual['and_count'], actual['and_depth'], actual['logical_cnot']) == (k, depth, cnot), name
                evidence = 'seed-0-witness-and-historical-record'
            else:
                evidence = 'historical-seed-0-record'
                record_only.append(name)
        qusat = {'width': width, 'cnot_outside_qand': cnot,
                 'cnot_estimate_4t': cnot + 9*k, 't_count': 4*k,
                 'online_t_depth': depth, 'evidence': evidence}
        native = lighter[name]
        assert native['verification'] == 'pass-16/16'
        x, c, q = int(native['X']), int(native['CNOT']), int(native['CCNOT'])
        assert int(native['t7']) == 7*q
        baseline = clean_wrapper(c, q)
        baseline['native_counts'] = {'X': x, 'CNOT': c, 'Toffoli': q}
        published = None
        if name in dorcis:
            source = dorcis[name]
            counts = source['native_counts']
            published = clean_wrapper(counts['CNOT'], counts['Toffoli'])
            published['circuit_index'] = source['circuit_index']
            published['native_counts'] = counts
            published['source_url'] = source['source_url']
            published['status'] = 'published-circuit; no synthesis rerun'
        rows.append({'sbox': name, 'qusat': qusat, 'lighter_r_wrapper': baseline, 'dorcis_wrapper': published})
    if require_all_witnesses and record_only:
        raise AssertionError('Gate-file coverage unavailable for: ' + ', '.join(record_only))
    return {
        'scope': 'Table 14 clean interface and specified 4T schedules; CNOT estimates include lowering without cross-gadget cancellation.',
        'width_scope': 'Declared QuSAT allocations versus a serial-scratch baseline wrapper; width is not a global minimum.',
        'record_only_extended_rows': record_only,
        'rows': rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-record', action='store_true')
    parser.add_argument('--require-all-witnesses', action='store_true')
    parser.add_argument('--output-json', type=Path)
    args = parser.parse_args()
    result = verify(require_all_witnesses=args.require_all_witnesses)
    if args.check_record:
        record = json.loads((ROOT/'results/r2/table14_check.json').read_text(encoding='utf-8'))
        if result != record:
            raise AssertionError('Table 14 conversion differs from the R2 validation record')
    payload = json.dumps(result, indent=2) + '\n'
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload, encoding='utf-8')
    print(payload, end='')


if __name__ == '__main__':
    main()
