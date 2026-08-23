# Anonymous SPN Quantum-Resource Verification Artifact

This repository is the anonymous verification artifact accompanying a revised
manuscript on depth-oriented logical-resource estimation for lightweight SPN
block ciphers.

The release is intentionally a **claim-verification package**, not a turnkey
release of the complete production framework. It contains a minimal public
reference SMT encoder and bounded search driver, fixed witnesses, forward/inverse
Boolean netlists, frozen SMT instances for all six primary S-boxes, independent
verification and accounting programs, solver records, external
benchmark metadata, and the frozen tables needed to audit the paper's main
claims. Production-only symmetry breaking, CNOT ranking, model-sampling,
parameter tuning, and experiment orchestration code are not included.

## What can be checked

- all six primary 4-bit S-box forward and inverse witnesses on all 16 inputs;
- all six reported fixed `k1/k2` synthesis shapes as directly rerunnable SMT-LIB2
  feasibility instances;
- LUT-to-SMT-to-SAT-to-netlist execution in the disclosed depth-2 AND-XOR space;
- the reported AND counts, AND depths, logical CNOT accounting, and 4T/7T
  component costs for the released netlists;
- the 24-CNOT, depth-5 MixColumn construction on all 65,536 column inputs;
- uLBC multi-round known-answer vectors and inverse restoration;
- reuse-safe fully parallel, four-group, and fully serial schedules;
- pair-parallel and pair-serial complete Grover-iteration resources;
- comparator, phase marking, encryption uncomputation, and diffusion costs;
- separate gate-count and depth-times-width search costs;
- the model/scope labels used in the revised cross-cipher table;
- rerun metadata for LIGHTER-R and published DORCIS context;
- primary and extended solver/runtime records without treating timeouts as
  UNSAT proofs.

## Repository layout

```text
data/
  external/             sanitized LIGHTER-R/DORCIS benchmark records
  netlists/             released forward/inverse Boolean witnesses
  reference/            S-box tables and uLBC known-answer vectors
  resource_model.json   explicit logical accounting assumptions
  solver/               six fixed SMT instances and bounded-search records
frozen_results/         manuscript-facing JSON/CSV evidence
src/
  mapping/              Boolean-netlist-to-resource verification helpers
  check_fixed_smt2.py    reruns and hash-checks all six frozen SMT instances
  reference_smt_encoder.py
                         minimal public fixed encoder and bounded search
  recompute_resource_tables.py
  verify_external_validation.py
  verify_mixcolumn.py
  verify_sbox_witnesses.py
  verify_table10_models.py
  verify_ulbc_multiround.py
tests/                  consistency tests for the released evidence
docs/                   scope, environment, method disclosure, and instructions
```

## Installation

Python 3.10 or later is recommended. Most checks use only the standard
library. Z3 is needed for the fixed instances and the reference encoder.

```text
python -m venv .venv
python -m pip install -r requirements.txt
```

There is deliberately no `run_all`, PowerShell driver, notebook, or automated
end-to-end synthesis command. The individual audit commands and their expected
outputs are documented in `docs/REPRODUCTION_GUIDE.md`.

## Important scope boundary

The released netlists are sufficient to verify the reported circuits and to
recompute the manuscript tables. The reference encoder regenerates the admitted
feasibility constraints but deliberately omits production CNOT ranking,
symmetry breaking, sampling, and orchestration. Consequently, an arbitrary SAT
model exported by the reference encoder need not have the same CNOT count as
the manuscript-selected witness. A timeout is `UNKNOWN`, never an UNSAT proof.
See `docs/ARTIFACT_SCOPE.md` before using the results.

## Anonymity

The repository contains no author names, affiliations, email addresses,
machine usernames, IP addresses, or absolute local paths. Bibliographic names
refer only to published prior work.

## License

See `LICENSE.txt`. Third-party tools are not vendored; upstream references and
commit identifiers are listed in `docs/THIRD_PARTY.md`.
