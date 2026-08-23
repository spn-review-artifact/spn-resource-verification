# Modular verification guide

Run commands from the repository root. No command regenerates the proprietary
search pipeline; each command checks one evidence layer.

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

This reference driver has no symmetry breaking or CNOT-ranking stage. It proves
fixed-shape feasibility and can establish bounded minimum AND count only when
all lower calls terminate UNSAT. A newly extracted SAT netlist is not promised
to match the CNOT count of the separately released manuscript witness.

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

The tests are separated by evidence layer and may be run individually, for
example:

```text
python -m unittest tests.test_artifact.SboxEvidenceTests -v
python -m unittest tests.test_artifact.ResourceEvidenceTests -v
python -m unittest tests.test_artifact.ExternalEvidenceTests -v
```

No single wrapper is supplied for installing dependencies, running searches,
executing all checks, and rebuilding manuscript tables.
