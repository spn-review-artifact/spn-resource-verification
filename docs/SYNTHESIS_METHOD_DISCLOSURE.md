# Public disclosure of the bounded S-box synthesis method

This document specifies the released search space and accompanies the minimal
source implementation in `src/reference_smt_encoder.py`. The authors'
production symmetry breaking, CNOT ranking, sampling, and orchestration code
remain outside the public artifact.

## Fixed feasibility problem

For a 4-input, 4-output S-box and a fixed pair `(k1, k2)`, the admitted circuit
has two nonlinear layers. The first layer contains `k1` AND gates. Each input of
each first-layer AND is an arbitrary GF(2)-linear form of the four S-box input
bits. The second layer contains `k2` AND gates. Each of its two inputs is an
arbitrary GF(2)-linear form of the four input bits and all first-layer AND
outputs. Each S-box output is an arbitrary affine GF(2) combination of the four
inputs and all `k1+k2` AND outputs.

Boolean coefficient variables select the terms in every linear form. For each
of the 16 possible inputs, the encoding symbolically evaluates both nonlinear
layers and constrains all four output bits to equal the target truth table. Each
AND operand is constrained to contain at least one selected coefficient. Thus,
a SAT result proves the existence of a circuit inside this exact depth-2
AND-XOR search space at the fixed `(k1, k2)` shape.

## Bounded search order and claims

The recorded search enumerates total AND count `k` in increasing order and
examines admitted partitions satisfying `k1+k2=k`, subject to the recorded
per-instance `k_max`, timeout, and random seed. A SAT model is converted to a
Boolean netlist and exhaustively checked on all 16 inputs. UNSAT is used as a
lower-bound statement only if the corresponding solver call terminates as
UNSAT. Timeout or UNKNOWN is retained as unresolved.

The released files provide three mutually checkable evidence layers:

1. `data/solver/*_fixed.smt2` freezes the exact constraints for the reported
   shape of each primary S-box;
2. `data/solver/primary_minimum_and_attempts.csv` and the retry JSON files
   disclose search bounds, partitions, statuses, runtimes, seeds, constraint
   counts, and SMT sizes; and
3. `data/netlists/forward/` provides compact SAT witnesses that are verified
   independently by `src/verify_sbox_witnesses.py`.

The fixed instances establish feasibility, while the bounded-search records
state whether the lower shapes were proved infeasible or remained unresolved.
No timeout is presented as a proof.

## Reimplementation boundary

An independent reader can use the released reference source to reconstruct the
admitted mathematical encoding, compare it with the frozen SMT-LIB2 files,
rerun the six instances in any conforming SMT solver, and validate extracted
witnesses. The included tests confirm that the reference encoder regenerates
the constraint sets of all six frozen primary instances.

The reference solver returns an arbitrary SAT model. It does not reproduce the
production candidate-ranking stage, so a newly extracted witness can have a
different CNOT count from the manuscript-selected fixed witness. The release
therefore supports end-to-end reference feasibility synthesis and complete
claim verification, but it does not claim byte-for-byte regeneration of the
production pipeline.
