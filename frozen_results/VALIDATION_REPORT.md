# Verification report

## R2 working-repository validation: 2026-11-25

This entry records a working-repository update, not a tagged archival release.

- Full consistency suite: 17 tests, PASS (Python 3.12.14, Z3 4.16.0).
- Rechecked on 2026-11-26: 17 tests, PASS (Python 3.10.0, Z3 4.15.4).
- Table 9 functional replay: 6 official vectors, 146 round-boundary states,
  and 12 multi-pair oracle cases, PASS.
- Table 14: all 8 rows match the manuscript's declared clean-interface and
  4T conversion, including native LIGHTER-R counts.
- The six primary QuSAT rows have released witness files; RECTANGLE and KLEIN
  use selected historical seed-0 records. These two rows have record-based
  conversion checks and are not counted as released gate files.
- GIFT's bounded-minimum status includes its existing conclusive 300-second
  UNSAT retry. PRINCE's unresolved lower instances remain UNKNOWN.
- Existing resource-model values and original result tables are unchanged.
- No release tag, archival record, or DOI is created by this update.

The functional replay models temporary-AND erasure and phase signs at the
logical basis-state level. Resource-model checks are separate from those
functional checks. Details are recorded in `results/r2/validation_report.json`.

## Historical validation

Validation date: 2026-09-02 (Asia/Shanghai)

The release candidate was checked from its repository root before packaging.

## Results

- nine consistency tests: PASS;
- six forward S-box witnesses: PASS 16/16 each;
- six inverse S-box witnesses: PASS 16/16 each;
- six old-state cleanup identities: PASS 16/16 each;
- representative uLBC fixed SMT instance: SAT;
- MixColumn exhaustive check: PASS 65,536/65,536;
- six uLBC encryption known-answer vectors: PASS;
- six uLBC inverse-restoration checks: PASS;
- reuse-safe encryption frozen rows: exact match;
- complete-oracle frozen rows: exact match;
- 23 revised Table 10 scope/model rows: PASS;
- six primary LIGHTER-R sanitized records: PASS;
- four extended benchmark families and 12 QuSAT seed records: PASS;
- anonymous-text scan: no machine username, IP address, author email, or
  absolute local path detected.

## Validation software

- standard-library verification and unit tests: Python 3.14.0;
- fixed SMT instance: Python 3.12.13 with Z3 4.16.0;
- release dependency pin for portable rerun: Z3 4.15.4.0, matching the Linux
  benchmark environment recorded in `docs/ENVIRONMENT.md`.

The repository contents were checked against `release_manifest.json` and
`SHA256SUMS.txt` after validation.
