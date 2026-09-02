# Release validation report

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
