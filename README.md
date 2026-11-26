# SPN Quantum-Resource Verification

This public verification package contains code and supporting data for
independently checking the reported quantum-resource results for lightweight
SPN block ciphers.

The R2 update adds the full-round and multi-pair oracle functional checks used
in Table 9, an eight-S-box Table 14 conversion checker, selected historical
seed-0 records, and the resolved GIFT bounded-minimum status. Existing
manuscript resource values are retained.

Quick checks from the repository root:

```text
python -B src/verify_r2_ulbc_gate_sequence.py --check-record
python -B src/verify_table14.py --check-record
python -B -m unittest discover -s tests -v
```

The first command checks six official vectors, 146 round-boundary states, and
12 multi-pair oracle cases. Temporary-AND erasure and phase signs are modeled
at the logical basis-state level. The second command checks the declared
clean-interface conversion and reports its witness coverage separately.

See `docs/PAPER_TABLE_MAP.md` for current manuscript table numbers and
`docs/R2_UPDATE.md` for the update scope and remaining original-file coverage.
The main branch remains open to continued development. A tagged archival
release and version-specific DOI are planned after acceptance and before
publication; this update creates neither.

It includes a reference SMT encoder and bounded-search driver, six fixed
primary SMT instances, released S-box witness netlists, resource-accounting
scripts, uLBC scheduling and MixColumn checks, independent verification
programs, per-attempt solver records, and frozen result tables. Python 3.10 or
later and Z3 are required for solver-based checks.

Start with:

- `docs/REPRODUCTION_GUIDE.md` for verification commands and expected results;
- `docs/ENVIRONMENT.md` for the separately recorded primary and extended
  execution environments;
- `docs/SYNTHESIS_METHOD_DISCLOSURE.md` for the admitted bounded S-box search
  space; and
- `docs/THIRD_PARTY.md` for external-source provenance.
