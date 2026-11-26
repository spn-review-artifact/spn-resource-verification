# Modular verification guide

The released files support modular checking of the reported witnesses, fixed
instances, resource tables, and validation data. They are intended for
independent verification of the reported results.

## R2 entry points

Current manuscript numbering is documented in `docs/PAPER_TABLE_MAP.md`.
The legacy filename `table10_main.csv` now corresponds to manuscript Table 13.

For the Table 9 functional checks:

```text
python -B src/verify_r2_ulbc_gate_sequence.py --check-record
```

Expected totals: six official encryption/inverse vectors, 146 round-boundary
states, and 12 multi-pair cases for r=2,3,4. Each case checks the joint flag,
ideal phase sign, comparator reversal, key restoration, and workspace cleanup.
The temporary-AND erasure is modeled by its logical action. These are functional
checks of reconstructed logical sequences, not physical Clifford+T simulation.
Resource tables are checked separately against their declared accounting model.

For Table 14 and its Table 1 CNOT convention:

```text
python -B src/verify_table14.py --check-record
```

Expected: eight S-box rows matching `results/r2/table14_check.json`. QuSAT's
CNOT estimate is CNOT-outside-QAND + 9k. A baseline clean wrapper has width 9,
CNOT estimate 2c+4+20q, T-count 8q, and online T-depth 2q, where c and q are
the native CNOT and Toffoli counts. QuSAT widths are the declared allocations;
baseline widths use serial scratch reuse. These are specified schedules.

Six primary QuSAT rows have released forward netlists. RECTANGLE and KLEIN
use their selected historical seed-0 records. Their table conversions are
checked against those records; original selected netlists are not included.
Strict gate-file coverage can be requested with:

```text
python -B src/verify_table14.py --require-all-witnesses
```

That strict check reports the two record-only rows as lacking gate-file
coverage. The normal check reports record-based and witness-based coverage
explicitly.

GIFT's minimum status includes the existing 300-second retry in
`data/solver/retry_300s_seed1.json`, which resolved the last four-AND partition
as UNSAT. PRINCE's two unresolved five-AND partitions remain UNKNOWN at the
600-second per-call limit. Here, k=6 denotes the AND count of the verified
depth-2 PRINCE implementation, rather than its unrestricted multiplicative
complexity; existence of a five-AND circuit within this encoding remains
unresolved.

## 1. Verify released S-box witnesses

```text
python src/verify_sbox_witnesses.py
```

Expected: twelve `pass-16/16` checks (six forward and six inverse), followed by
`all released S-box witnesses verified`.

## 2. Check all six fixed SMT instances

```text
python src/check_fixed_smt2.py
```

Expected: six `sat` results followed by `all_fixed_instances_verified=6/6`.
The checker first verifies each file against the size and SHA-256 value in
`data/solver/fixed_instances.json`, then reruns the PRESENT, GIFT, Midori,
PRINCE, SKINNY, and uLBC feasibility instances. These files do not regenerate
the encoding and do not turn unresolved lower instances into UNSAT proofs.

## 3. Regenerate a fixed instance with the public reference encoder

The following command starts from the uLBC LUT in the released catalog,
constructs the disclosed `k1=1, k2=3` constraints, solves them, exports one SAT
model as a netlist, and exhaustively checks all 16 inputs:

```text
python src/reference_smt_encoder.py --cipher uLBC --k1 1 --k2 3 \
  --timeout-ms 60000 --seed 0 \
  --smt2 generated/ulbc_reference.smt2 \
  --netlist generated/ulbc_reference.netlist \
  --summary-json generated/ulbc_reference.json
```

Expected: `solver_status` is `sat` and `truth_table_check` is `pass-16/16`.
The tests additionally confirm that the public encoder reconstructs the exact
constraint set in every released primary frozen instance.

To exercise the increasing-`k` driver on a trivial affine permutation:

```text
python src/reference_smt_encoder.py --lut 0123456789ABCDEF --k-max 0
```

The reference driver proves fixed-shape feasibility and can establish bounded
minimum AND count only when all lower calls terminate UNSAT. Because an SMT
solver may return any satisfying model, a newly extracted SAT netlist is not
expected to be identical to the separately released manuscript witness.

## 4. Verify MixColumn

```text
python src/verify_mixcolumn.py
```

Expected: six CNOTs per bit slice, 24 per column, physical ASAP depth 5, and
`pass-65536/65536`.

## 5. Verify complete uLBC cipher instances

```text
python src/verify_ulbc_multiround.py
```

Expected: all six known-answer vectors encrypt correctly and inverse execution
restores all six plaintexts.

## 6. Recompute resource and Grover tables

```text
python src/recompute_resource_tables.py --check-frozen
```

This recomputes the three S-box schedules, both plaintext-pair schedules, the
complete iteration, exact-7T sensitivity, G-cost, and DW-cost. It checks the
results against `frozen_results/` without overwriting those files.

To write a separate generated copy:

```text
python src/recompute_resource_tables.py --output-dir generated
```

## 7. Audit the revised cross-cipher table

```text
python src/verify_table10_models.py
```

The check enforces explicit `1E/2E`, 4T, exact-7T, and unitary-decomposition
labels and rejects percentage comparisons across unmatched models/scopes.

## 8. Inspect external validation records

```text
python src/verify_external_validation.py
```

This checks the sanitized LIGHTER-R summaries, the clean-wrapper arithmetic,
the QuSAT component arithmetic, and the explicit distinction between rerun
data and DORCIS published-only values.

## 9. Run consistency tests

Run the full consistency-test suite with:

```text
python -m unittest discover -s tests -v
```

The tests are also separated by evidence layer and may be run individually,
for example:

```text
python -m unittest tests.test_artifact.SboxEvidenceTests -v
python -m unittest tests.test_artifact.ResourceEvidenceTests -v
python -m unittest tests.test_artifact.ExternalEvidenceTests -v
```
