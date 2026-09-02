# SPN Quantum-Resource Verification

This public verification package contains code and supporting data for
independently checking the reported quantum-resource results for lightweight
SPN block ciphers.

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
