# Reviewer-comment to public-evidence map

This map identifies which released file supports each code- or data-facing
revision. Manuscript-only framing and citation changes are identified as such.

## Reviewer 2

| Comment | Public evidence | Status in artifact |
|---|---|---|
| Standard Grover metrics | `src/recompute_resource_tables.py`, `frozen_results/complete_oracle/` | G-cost and DW-cost are separate |
| Complete oracle accounting | same files | comparator, phase mark, reversal, encryption uncomputation, diffusion included |
| Optimistic logical assumptions | `data/resource_model.json`, `frozen_results/table10_main.csv` | 4T and exact-7T sensitivities separated |
| Limited validation | `src/verify_sbox_witnesses.py`, `src/verify_mixcolumn.py`, `src/verify_external_validation.py`, `data/external/` | primary plus broader external records |
| IoT deployment caution | manuscript discussion | no new device-data claim in artifact |
| Public optimizer, scripts, and netlists | `src/reference_smt_encoder.py`, `data/netlists/`, all six fixed instances in `data/solver/`, and verification programs in `src/` | minimal source-level synthesis path and complete claim verification; production heuristics remain outside the release |
| Moderate resilience/suitability claims | manuscript discussion | resource outputs contain no NIST-category claim |

## Reviewer 3

| Comment | Public evidence | Status in artifact |
|---|---|---|
| Normalize mixed cost models | `frozen_results/table10_main.csv`, `src/verify_table10_models.py` | scopes and gate models explicit |
| Pair-parallel width/depth consistency | `src/recompute_resource_tables.py`, `frozen_results/complete_oracle/` | parallel and serial rows both present |
| Replace nonstandard scalar indicator | same complete-oracle files | search G and DW exponents separate |
| Attribute prior methods and add baselines | `docs/THIRD_PARTY.md`, `data/external/` | original sources identified |
| Solver runtime, kmax, constraints, hardware | `data/solver/`, `docs/ENVIRONMENT.md` | recorded values and Intel Xeon 8352V topology released |
| S-box schedule extremes | `frozen_results/reuse_safe_ulbc/` | fully parallel, four-group, fully serial |
| Encryption-level full depth | same files | compiled full-depth upper bounds released |
| First screening stage terminology | manuscript discussion | no code claim |
| Energy/protocol integration | manuscript discussion | no device-energy data fabricated |

## Release limitation

The public package verifies the numerical claims but is not the complete QuSAT
development repository. This limitation is explicit rather than hidden. The
production symmetry breaking, CNOT ranking, sampling, and orchestration remain
unreleased. A minimal reference encoder, a basic increasing-`k` driver, six fixed
primary instances, complete status records, and all citation-facing witnesses
are public.
