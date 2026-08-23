# coding: utf-8
"""
State Manager
Replaces three functions from classical_to_quantum.sage:
  - check_two_states_qubits()
  - select_step()
  - get_state_transform_matrix()

These implement the register liveness analysis: deciding which qubits
can be cleaned to |0> (zero states) vs which must keep their value
(nonzero states), and computing the GF(2) matrix for each CNOT sub-circuit.
"""

from gf2_matrix import GF2Matrix, identity
from linear_parser import linears_to_matrix


def check_two_states_qubits(states: list, n: int, dim: int):
    """
    Classify qubits into nonzero and zero states.

    Greedily selects qubits from front to back whose affine expressions
    increase the rank of the current set.  Remaining qubits are 'zero'
    states — linearly dependent, so they can be reset to |0> by CNOT gates.

    Parameters
    ----------
    states : list of str
        Current affine expression of each qubit (e.g. "X0+M1", "", "X2").
        Empty string "" represents a qubit already in state |0>.
    n   : int  Number of X input variables.
    dim : int  Total number of variables (X + M visible so far) = matrix columns.

    Returns
    -------
    nonzero_qubits : list of int
    zero_qubits    : list of int
    """
    states_n = len(states)
    nonzero_states = []
    nonzero_qubits = []

    for i in range(states_n):
        rank1 = linears_to_matrix(nonzero_states, n=n, cols=dim).rank()
        if rank1 == dim:          # already full rank — no more nonzero needed
            break
        nonzero_states.append(states[i])
        rank2 = linears_to_matrix(nonzero_states, n=n, cols=dim).rank()
        if rank2 == rank1:        # rank unchanged → this state is dependent
            nonzero_states.pop()
        else:
            nonzero_qubits.append(i)

    zero_qubits = [i for i in range(states_n) if i not in set(nonzero_qubits)]
    return nonzero_qubits, zero_qubits


def select_step(initial_states: list, candidate_states: list,
                n: int, dim: int, target_n: int):
    """
    Select states from candidates to achieve full column rank, then pad
    with zero states to reach target_n total states.

    Parameters
    ----------
    initial_states   : list of str  States that must be included (required).
    candidate_states : list of str  Pool to select from.
    n        : int  Number of X input variables.
    dim      : int  Number of matrix columns (total variables).
    target_n : int  Desired total length of returned list.

    Returns
    -------
    selected_states : list of str  Length == target_n.
    """
    states_n = len(candidate_states)
    selected_states = initial_states[:]
    nonzero_idxs = []

    # Phase 1: greedily pick linearly independent states until rank = dim
    for i in range(states_n):
        rank1 = linears_to_matrix(selected_states, n=n, cols=dim).rank()
        if rank1 == dim:
            break
        selected_states.append(candidate_states[i])
        rank2 = linears_to_matrix(selected_states, n=n, cols=dim).rank()
        if rank2 == rank1:
            selected_states.pop()          # dependent → skip
        else:
            nonzero_idxs.append(i)

    # Phase 2: fill remaining slots with zero (dependent) states
    zero_idxs = [i for i in range(states_n) if i not in set(nonzero_idxs)]
    remaining = target_n - len(selected_states)
    zero_states = [candidate_states[i] for i in zero_idxs[:remaining]]
    selected_states = selected_states + zero_states

    return selected_states


def get_state_transform_matrix(S_pre: list, S: list,
                                n: int, dim: int) -> GF2Matrix:
    """
    Compute the invertible GF(2) matrix MT such that MT * A = B, where
      A = linears_to_matrix(S_pre)
      B = linears_to_matrix(S)
    This matrix encodes the CNOT sub-circuit that maps the qubit states
    from S_pre to S.

    Parameters
    ----------
    S_pre : list of str  Affine expressions before the CNOT sub-circuit.
    S     : list of str  Affine expressions after  the CNOT sub-circuit.
    n     : int  Number of X input variables.
    dim   : int  Number of matrix columns.

    Returns
    -------
    MT : GF2Matrix (square, invertible)
    """
    A = linears_to_matrix(S_pre, n=n, cols=dim)
    B = linears_to_matrix(S,     n=n, cols=dim)

    # T_A satisfies: T_A * A = RREF(A)
    # T_B satisfies: T_B * B = RREF(B)
    # If RREF(A) == RREF(B), then T_A * A = T_B * B
    # => B = T_B^{-1} * T_A * A  =>  MT = T_B^{-1} * T_A
    _, T_A = A.extended_echelon_form()
    _, T_B = B.extended_echelon_form()

    MT = T_B.inverse() * T_A
    return MT


# ------------------------------------------------------------------ #
# Self-test
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    print("=== state_manager self-test ===\n")

    # ---- Test 1: check_two_states_qubits ----
    # states over 2 variables (X0, X1), dim=2
    # "X0"    → rank contribution: 1
    # "X1"    → rank contribution: 2
    # "X0+X1" → dependent on X0 and X1 → zero state
    states = ["X0", "X1", "X0+X1"]
    nz, z = check_two_states_qubits(states, n=2, dim=2)
    print(f"states = {states}")
    print(f"nonzero_qubits = {nz}  (expected [0, 1])")
    print(f"zero_qubits    = {z}   (expected [2])")
    assert nz == [0, 1], f"nz wrong: {nz}"
    assert z  == [2],    f"z wrong:  {z}"
    print("[PASS]\n")

    # ---- Test 2: check_two_states_qubits with empty state ----
    # "" represents |0>, contributes nothing to rank
    states2 = ["X0", "", "X1", "X0+X1"]
    nz2, z2 = check_two_states_qubits(states2, n=2, dim=2)
    print(f"states2 = {states2}")
    print(f"nonzero_qubits = {nz2}  (expected [0, 2])")
    print(f"zero_qubits    = {z2}   (expected [1, 3])")
    assert nz2 == [0, 2],    f"nz2 wrong: {nz2}"
    assert set(z2) == {1, 3}, f"z2 wrong:  {z2}"
    print("[PASS]\n")

    # ---- Test 3: select_step ----
    # n=3, dim=3, initial=["X0"], candidates=["X1","X0+X1","X2"], target_n=4
    # Phase 1: X1 (rank 2), X0+X1 dependent → skip, X2 (rank 3=dim) → stop
    #   selected so far: ["X0","X1","X2"]
    # Phase 2: zero states = ["X0+X1"], fill to target_n=4
    #   result: ["X0","X1","X2","X0+X1"]
    initial    = ["X0"]
    candidates = ["X1", "X0+X1", "X2"]
    selected   = select_step(initial, candidates, n=3, dim=3, target_n=4)
    print(f"initial    = {initial}")
    print(f"candidates = {candidates}")
    print(f"selected   = {selected}  (len={len(selected)}, expected 4)")
    assert len(selected) == 4, f"Wrong length: {len(selected)}"
    # verify rank of first 3 selected equals dim=3
    mat_sel = linears_to_matrix(selected[:3], n=3, cols=3)
    print(f"rank(selected[:3]) = {mat_sel.rank()}  (expected 3)")
    assert mat_sel.rank() == 3
    assert selected[-1] == "X0+X1", f"Last element should be zero state: {selected[-1]}"
    print("[PASS]\n")

    # ---- Test 4: get_state_transform_matrix ----
    # S_pre = I (identity basis: X0, X1, X2)
    # S     = B (simple row operation: row0 ^= row1)
    # MT should map I to B, so MT = B itself
    S_pre = ["X0",      "X1", "X2"]
    S     = ["X0+X1",   "X1", "X2"]
    MT = get_state_transform_matrix(S_pre, S, n=3, dim=3)
    print(f"MT (should map X0->X0+X1, X1->X1, X2->X2):")
    print(MT)

    # Verify: MT * A = B
    A = linears_to_matrix(S_pre, n=3, cols=3)
    B = linears_to_matrix(S,     n=3, cols=3)
    MT_A = MT * A
    print(f"\nMT * A:\n{MT_A}")
    print(f"B:\n{B}")
    assert MT_A == B, f"MT*A != B"
    print("[PASS]\n")

    # ---- Test 5: MT invertibility ----
    MT_inv = MT.inverse()
    I3 = identity(3)
    assert MT * MT_inv == I3, "MT not invertible"
    print("[PASS] MT is invertible\n")

    # ---- Test 6: more complex transform ----
    S_pre2 = ["X0",       "X1",       "X2",    "X0+X1"]
    S2     = ["X0+X2",    "X1+X2",    "X0+X1", "X2"]
    MT2 = get_state_transform_matrix(S_pre2, S2, n=3, dim=3)
    A2  = linears_to_matrix(S_pre2, n=3, cols=3)
    B2  = linears_to_matrix(S2,     n=3, cols=3)
    assert MT2 * A2 == B2, "Test 6 failed"
    print("[PASS] complex transform\n")

    print("=== All tests passed ===")
