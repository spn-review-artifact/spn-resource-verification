# Third-party sources

Third-party repositories are not vendored into this package.

## LIGHTER-R

- Repository: https://github.com/vdasu/lighter-r
- Released rerun commit: `146608220e30e47a4521947933b618e20f53f624`
- Paper: V. A. Dasu, A. Baksi, S. Sarkar, and A. Chattopadhyay,
  "LIGHTER-R: Optimized Reversible Circuit Implementation for SBoxes," 2019.
- DOI: https://doi.org/10.1109/SOCC46988.2019.1570548320

The sanitized summaries under `data/external/` contain the executed parameters
and verified resource results, but not upstream source code.

## DORCIS

- Paper: M. Chun, A. Baksi, and A. Chattopadhyay, "DORCIS: Depth Optimized
  Quantum Implementation of Substitution Boxes," 2023.
- URL: https://eprint.iacr.org/2023/286

DORCIS values in this artifact are explicitly labelled `published-only` and
are not described as locally rerun results.

## LWC-Q / Bijwe et al.

- Repository: https://github.com/amitcrypto/LWC-Q
- Paper DOI: https://doi.org/10.1007/978-3-031-22301-3_5

Only normalized citation-facing rows and provenance notes are retained here;
the upstream Q# implementation is not copied.

## Z3

- Project: https://github.com/Z3Prover/z3
- Python package pinned for the released fixed instance: 4.15.4.0

## uLBC specification

The reference permutation, constants, and known-answer vectors used by the
verification program follow the public cipher specification and public VHDL
testbench. Their inclusion is for interoperability testing, not a claim of
authorship over the cipher design.
