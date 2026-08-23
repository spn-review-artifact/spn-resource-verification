# Artifact scope and intellectual-property boundary

## Released

This public package releases the evidence required to inspect the numerical
claims in the revised manuscript:

1. one forward and one inverse Boolean witness for each primary 4-bit S-box;
2. fixed SMT-LIB2 feasibility instances for the reported `k1/k2` shapes of all
   six primary S-boxes;
3. a minimal source-level reference encoder and increasing-`k` bounded search
   driver for the disclosed depth-2 AND-XOR space;
4. solver status, runtime, constraint-count, SMT-size, seed, and timeout
   records for the bounded searches used by the paper;
5. independent exhaustive truth-table and MixColumn verifiers;
6. uLBC multi-round known-answer verification;
7. explicit reuse-safe encryption and complete-oracle accounting formulas;
8. pair- and S-box-scheduling extremes;
9. the frozen cross-cipher model ledger;
10. sanitized LIGHTER-R rerun records and DORCIS published context; and
11. hashes and tests that detect accidental changes to citation-facing data.

## Deliberately excluded

The following implementation details are retained by the authors:

- the production QuSAT constraint generator beyond the released reference
  encoding;
- production search-order refinements, symmetry breaking, candidate ranking,
  and model-sampling code;
- automated CNOT-provenance recovery and parameter-tuning utilities;
- cluster launchers, batch schedulers, and one-click reproduction scripts;
- unpublished experimental branches and unsuccessful optimization drafts; and
- author-side manuscript/build infrastructure.

The boundary protects the authors' implementation know-how while allowing an
independent reader to regenerate the disclosed feasibility constraints, rerun a
basic bounded search, check the released witnesses, recompute the tables, and
inspect the exact assumptions used in the paper.

## Claim boundary

- `SAT` plus an exhaustive truth-table check establishes that a released
  witness implements the stated S-box.
- The six fixed SAT instances establish feasibility at the released shapes;
  they are not, by themselves, minimum-AND certificates.
- The reference encoder selects an arbitrary SAT model. Since production CNOT
  ranking is not released, its newly extracted witness may have a different
  CNOT count from the manuscript-selected netlist without contradicting the
  feasibility result.
- `UNSAT` is used as a lower-bound result only when the corresponding bounded
  solver call terminated as UNSAT.
- `UNKNOWN` or timeout is never promoted to UNSAT.
- GIFT and PRINCE are therefore labelled verified best-found witnesses where
  a lower instance remained unresolved under the recorded timeout.
- Full depths are compiled logical upper bounds, not physical hardware depths.
- 4T values use measurement-assisted temporary logical ANDs. Exact-7T values
  are a unitary Toffoli sensitivity, not a physical surface-code estimate.
- External published values are not represented as locally synthesized data.

## Reuse

Public visibility does not place the code in the public domain. The
research-verification license in `LICENSE.txt` applies to original files in
this package; third-party material remains under its upstream terms.
