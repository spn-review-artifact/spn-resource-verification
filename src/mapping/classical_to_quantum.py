# coding: utf-8
"""
Classical to Quantum Algorithm
Pure Python implementation of classical_to_quantum() from classical_to_quantum.sage.

Input:  classical Boolean circuit using {NOT, XOR, AND}
Output: quantum circuit structure (CNOT layers + Toffoli layers + GF(2) matrices)

No SageMath required.
"""

from gf2_matrix import GF2Matrix
from linear_parser import linears_to_matrix, parse_circuit
from state_manager import check_two_states_qubits, select_step, get_state_transform_matrix


# ------------------------------------------------------------------ #
# Data class
# ------------------------------------------------------------------ #
class QuantumCircuitInfo:
    """
    Stores the layered structure of the quantum circuit.

    Attributes
    ----------
    n, m : int
        Number of inputs / outputs.
    s : int
        T-depth (= AND-depth of the classical circuit).
    width : int
        Total number of qubits.
    CNOT_layers_qubits : list of list of int
        Qubit indices involved in each CNOT sub-circuit (s+1 entries).
    Toffoli_layers_qubits : list of list of int
        Qubit indices that are OUTPUTS of Toffoli gates in each layer (s entries).
    state_transform_matrices : list of GF2Matrix
        Invertible GF(2) matrices encoding each CNOT sub-circuit (s+1 entries).
    """

    def __init__(self, n, m, s, width,
                 CNOT_layers_qubits,
                 Toffoli_layers_qubits,
                 state_transform_matrices,
                 Y_const_flips=None):
        self.n = n
        self.m = m
        self.s = s
        self.width = width
        self.CNOT_layers_qubits       = CNOT_layers_qubits
        self.Toffoli_layers_qubits    = Toffoli_layers_qubits
        self.state_transform_matrices = state_transform_matrices
        # Y_const_flips[k] = 1 means output qubit k has a constant-1 offset (NOT gate)
        self.Y_const_flips = Y_const_flips if Y_const_flips is not None else [0] * m

    def print_info(self):
        print(f"# quantum circuit info")
        print(f"# n={self.n}, m={self.m}, T-depth={self.s}, width={self.width}")
        for i in range(self.s):
            print(f"# --- Layer {i+1} ---")
            print(f"#   CNOT qubits   : {self.CNOT_layers_qubits[i]}")
            print(f"#   Toffoli qubits: {self.Toffoli_layers_qubits[i]}")
            print(f"#   CNOT matrix   :")
            for row in self.state_transform_matrices[i].data:
                print(f"#     {row}")
        print(f"# --- Output CNOT ---")
        print(f"#   CNOT qubits: {self.CNOT_layers_qubits[-1]}")
        print(f"#   CNOT matrix:")
        for row in self.state_transform_matrices[-1].data:
            print(f"#     {row}")


# ------------------------------------------------------------------ #
# Output layer handler (last AND layer + Y output CNOT)
# ------------------------------------------------------------------ #
def _output_part(n, m, cur_dim, cur_states, Bs, By):
    """
    Handle the last AND layer (depth s) and the output Y CNOT sub-circuit.

    Returns
    -------
    (dim, width, CNOT_layers_qubits, Toffoli_layers_qubits, state_transform_matrices)
    """
    dim    = cur_dim
    states = cur_states[:]
    width  = len(states)
    qubits = list(range(width))

    CNOT_layers_qubits       = []
    Toffoli_layers_qubits    = []
    state_transform_matrices = []

    # ---- Compute ancilla requirements for last AND layer ----
    ns = len(Bs) // 2
    a  = 2 * ns - linears_to_matrix(Bs, n=n, cols=dim).rank()

    nonzero_qubits, zero_qubits = check_two_states_qubits(states, n=n, dim=dim)
    zero_states    = [states[i] for i in zero_qubits]
    nonzero_states = [states[i] for i in nonzero_qubits]
    zero_states_n  = len(zero_states)

    # Always allocate at least m fresh qubits for Y outputs
    allocate_n        = m
    clean_toffoli_out = 0

    if ns <= m:
        allocate_n += max(a - zero_states_n, 0)
    else:
        if a - zero_states_n > 0:
            allocate_n += (a - zero_states_n) + (ns - m)
        else:
            clean_toffoli_out = min(zero_states_n - a, ns - m)
            allocate_n       += (ns - m) - clean_toffoli_out

    # Allocate new qubits (appended as |0> = "" states)
    zero_states += [""] * allocate_n
    zero_qubits += [width + i for i in range(allocate_n)]
    states      += [""] * allocate_n
    qubits      += [width + i for i in range(allocate_n)]
    width       += allocate_n

    # Qubit assignments for CNOT and Toffoli
    CNOT_n         = dim + a + clean_toffoli_out
    CNOT_qubits    = nonzero_qubits[:] + zero_qubits[:a + clean_toffoli_out]
    extra_t        = max(0, ns - m)       # Toffoli outputs that go to old zero qubits
    Toffoli_qubits = (zero_qubits[a:a + extra_t] + zero_qubits[-m:])[:ns]

    # Select CNOT sub-circuit states
    Ss_pre = nonzero_states[:] + zero_states[:a + clean_toffoli_out]
    Ss = select_step(
        initial_states=Bs,
        candidate_states=Ss_pre,
        n=n, dim=dim,
        target_n=CNOT_n - clean_toffoli_out
    )
    Ss += [""] * clean_toffoli_out

    MT = get_state_transform_matrix(Ss_pre, Ss, n=n, dim=dim)

    # Update qubit states
    for j in range(CNOT_n):
        states[CNOT_qubits[j]] = Ss[j]
    for j in range(ns):
        states[Toffoli_qubits[j]] = f"M{dim - n + j}"
    dim += ns

    CNOT_layers_qubits.append(CNOT_qubits)
    Toffoli_layers_qubits.append(Toffoli_qubits)
    state_transform_matrices.append(MT)

    # ---- Output Y CNOT sub-circuit ----
    # Goal: find a CNOT circuit that writes Y0..Ym-1 into outputs_qubits.
    outputs_qubits = qubits[-m:]   # last m qubits (currently |0>)

    nonzero_qubits_y, zero_qubits_y = check_two_states_qubits(states, n=n, dim=dim)

    # CNOT operates on: output qubits (first) + all nonzero qubits
    CNOT_qubits_y = outputs_qubits[:]
    for q in nonzero_qubits_y:
        if q not in CNOT_qubits_y:
            CNOT_qubits_y.append(q)

    # Y_pre: current states of the CNOT qubits
    # Y_states: desired states after CNOT  (starts with By = Y expressions)
    # Both must have the same length for the square transformation matrix
    Y_pre    = [states[i] for i in CNOT_qubits_y]
    target_n = len(CNOT_qubits_y)          # ← must match len(Y_pre)

    Y_states = select_step(
        initial_states=By,
        candidate_states=Y_pre,
        n=n, dim=dim,
        target_n=target_n
    )

    MT_Y = get_state_transform_matrix(Y_pre, Y_states, n=n, dim=dim)

    CNOT_layers_qubits.append(CNOT_qubits_y)
    state_transform_matrices.append(MT_Y)

    # Constant-1 terms in the output expressions → NOT gates on output qubits
    Y_const_flips = [1 if "1" in by.split("+") else 0 for by in By]

    return dim, width, CNOT_layers_qubits, Toffoli_layers_qubits, state_transform_matrices, Y_const_flips


# ------------------------------------------------------------------ #
# Main algorithm
# ------------------------------------------------------------------ #
def classical_to_quantum(n: int, m: int, s: int, C: list) -> QuantumCircuitInfo:
    """
    Convert a classical Boolean circuit to a quantum circuit structure.

    Parameters
    ----------
    n : int    Number of inputs  (X0 .. Xn-1).
    m : int    Number of outputs (Y0 .. Ym-1).
    s : int    AND-depth of the circuit.
    C : list   Operations in topological order, e.g.
               ["T1=X0+X3", "M0=T1*X2", "Y0=M0+X1"].

    Returns
    -------
    QuantumCircuitInfo
    """
    print(f"[c2q] n={n}, m={m}, AND-depth={s}")

    # Parse circuit → linear expression layers B[0..s+1]
    L, detected_s, total_M = parse_circuit(n=n, m=m, C=C)
    if detected_s != s:
        raise ValueError(f"Declared AND-depth={s} but detected {detected_s}")
    B = L

    # Initialise quantum register
    width  = n
    states = [f"X{i}" for i in range(n)]
    qubits = list(range(n))
    dim    = n

    CNOT_layers_qubits       = []
    Toffoli_layers_qubits    = []
    state_transform_matrices = []

    # ---- Middle AND layers: i = 1 .. s-1 ----
    for i in range(1, s):
        ni = len(B[i]) // 2
        ai = 2 * ni - linears_to_matrix(B[i], n=n, cols=dim).rank()

        nonzero_qubits, zero_qubits = check_two_states_qubits(states, n=n, dim=dim)
        zero_states    = [states[j] for j in zero_qubits]
        nonzero_states = [states[j] for j in nonzero_qubits]
        zero_states_n  = len(zero_states)

        clean_toffoli_out = max(0, min(zero_states_n - ai, ni))
        allocate_n        = max(0, ni + ai - zero_states_n)

        if allocate_n > 0:
            zero_states += [""] * allocate_n
            zero_qubits += [width + j for j in range(allocate_n)]
            states      += [""] * allocate_n
            qubits      += [width + j for j in range(allocate_n)]
            width       += allocate_n

        CNOT_n         = dim + ai + clean_toffoli_out
        CNOT_qubits    = nonzero_qubits[:] + zero_qubits[:ai + clean_toffoli_out]
        Toffoli_qubits = zero_qubits[ai:ai + ni]   # ni always positive here

        Si_pre = nonzero_states[:] + zero_states[:ai + clean_toffoli_out]
        Si = select_step(
            initial_states=B[i],
            candidate_states=Si_pre,
            n=n, dim=dim,
            target_n=CNOT_n - clean_toffoli_out
        )
        Si += [""] * clean_toffoli_out

        MT = get_state_transform_matrix(Si_pre, Si, n=n, dim=dim)

        for j in range(CNOT_n):
            states[CNOT_qubits[j]] = Si[j]
        for j in range(ni):
            states[Toffoli_qubits[j]] = f"M{dim - n + j}"
        dim += ni

        CNOT_layers_qubits.append(CNOT_qubits)
        Toffoli_layers_qubits.append(Toffoli_qubits)
        state_transform_matrices.append(MT)

    # ---- Last AND layer + output Y ----
    (dim, width,
     out_CNOT_q, out_Toffoli_q, out_MT, Y_const_flips) = _output_part(
        n=n, m=m, cur_dim=dim, cur_states=states,
        Bs=B[s], By=B[s + 1]
    )
    CNOT_layers_qubits       += out_CNOT_q
    Toffoli_layers_qubits    += out_Toffoli_q
    state_transform_matrices += out_MT

    print(f"[c2q] -> width={width}, total_M={total_M}")

    return QuantumCircuitInfo(
        n=n, m=m, s=s, width=width,
        CNOT_layers_qubits=CNOT_layers_qubits,
        Toffoli_layers_qubits=Toffoli_layers_qubits,
        state_transform_matrices=state_transform_matrices,
        Y_const_flips=Y_const_flips,
    )


# ------------------------------------------------------------------ #
# Verification: simulate the quantum circuit and check against truth table
# ------------------------------------------------------------------ #
def verify_circuit(qc: QuantumCircuitInfo, truth_table: list) -> bool:
    """
    Verify the quantum circuit by simulating all 2^n inputs and comparing
    with the provided truth table.

    Parameters
    ----------
    qc          : QuantumCircuitInfo
    truth_table : list of int, length 2^n
                  truth_table[x] = expected output value for input x

    Returns
    -------
    True if all 2^n inputs produce correct outputs, False otherwise.
    """
    n, m = qc.n, qc.m
    correct = 0

    for x in range(1 << n):
        # Initial qubit state: first n qubits = input bits, rest = 0
        N = [(x >> i) & 1 for i in range(n)] + [0] * (qc.width - n)

        # Simulate CNOT sub-circuits and Toffoli layers
        for layer_i in range(qc.s):
            CNOT_qubits    = qc.CNOT_layers_qubits[layer_i]
            Toffoli_qubits = qc.Toffoli_layers_qubits[layer_i]
            MT             = qc.state_transform_matrices[layer_i]

            # CNOT sub-circuit: linear transformation over GF(2)
            inputs  = [N[q] for q in CNOT_qubits]
            outputs = MT * inputs          # GF2Matrix * list → list of ints
            for j, q in enumerate(CNOT_qubits):
                N[q] = outputs[j]

            # Toffoli gates: controls are outputs[2j] and outputs[2j+1]
            # (the first 2*ni CNOT outputs are the AND-gate input pairs)
            for j, t in enumerate(Toffoli_qubits):
                N[t] ^= outputs[2 * j] & outputs[2 * j + 1]

        # Output CNOT sub-circuit
        CNOT_qubits_y = qc.CNOT_layers_qubits[-1]
        MT_Y          = qc.state_transform_matrices[-1]
        inputs_y      = [N[q] for q in CNOT_qubits_y]
        outputs_y     = MT_Y * inputs_y
        for j, q in enumerate(CNOT_qubits_y):
            N[q] = outputs_y[j]

        # Apply constant-1 NOT gates on output qubits
        for k in range(m):
            if qc.Y_const_flips[k]:
                N[-(m - k)] ^= 1

        # Read output: last m qubits
        out_bits = N[-m:]
        out_val  = sum(out_bits[i] << i for i in range(m))

        if out_val == truth_table[x]:
            correct += 1

    print(f"[verify] {correct}/{1 << n} correct")
    return correct == (1 << n)


# ------------------------------------------------------------------ #
# Self-test
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    print("=== classical_to_quantum self-test ===\n")

    # ---- Simple AND-depth-1 circuit ----
    # f(x0,x1) = x0 AND x1  (1 AND gate, depth 1)
    C1 = ["M0=X0*X1", "Y0=M0+0"]   # Y0 = X0 AND X1, no XOR needed
    # Actually need a valid XOR op for "Y0=M0+0"; let's just use assignment
    # Better: use a circuit where Y0 = M0
    C1 = ["M0=X0*X1", "T0=M0+M0",  # T0 = 0 (self-XOR trick, not useful)
          "Y0=X0+X0"]               # This is wrong, let me use a proper example

    # Use a clean AND-depth-1 example: Y0 = (X0+X1)*(X2+X3)
    C1 = [
        "T0=X0+X1",
        "T1=X2+X3",
        "M0=T0*T1",
        "Y0=M0+X0",    # Y0 = M0 XOR X0 (just to have a proper output)
    ]
    n1, m1, s1 = 4, 1, 1
    qc1 = classical_to_quantum(n=n1, m=m1, s=s1, C=C1)
    qc1.print_info()

    print(f"\nwidth={qc1.width}")
    assert qc1.s == 1
    assert len(qc1.CNOT_layers_qubits)    == s1 + 1
    assert len(qc1.Toffoli_layers_qubits) == s1
    print("[PASS] AND-depth-1 structure check\n")

    # ---- AND-depth-2 circuit from linear_parser test ----
    n2, m2, s2 = 4, 2, 2
    C2 = [
        "T1=X0+X1",
        "T2=X2+X3",
        "M0=T1*T2",    # AND depth 1
        "T3=X0+M0",
        "T4=X1+X2",
        "M1=T3*T4",    # AND depth 2
        "Y0=X0+M1",
        "Y1=M0+M1",
    ]
    qc2 = classical_to_quantum(n=n2, m=m2, s=s2, C=C2)
    qc2.print_info()

    assert qc2.s == 2
    assert len(qc2.CNOT_layers_qubits)    == s2 + 1
    assert len(qc2.Toffoli_layers_qubits) == s2
    assert qc2.width >= max(n2, m2)
    print(f"[PASS] AND-depth-2 structure check (width={qc2.width})\n")

    # ---- Verify AND-depth-2 circuit against truth table ----
    # Manually compute truth table for C2:
    # M0 = (X0^X1) & (X2^X3)
    # M1 = (X0^M0) & (X1^X2)
    # Y0 = X0 ^ M1
    # Y1 = M0 ^ M1
    tt = []
    for x in range(16):
        x0 = (x >> 0) & 1
        x1 = (x >> 1) & 1
        x2 = (x >> 2) & 1
        x3 = (x >> 3) & 1
        m0 = (x0 ^ x1) & (x2 ^ x3)
        m1 = (x0 ^ m0)  & (x1 ^ x2)
        y0 = x0 ^ m1
        y1 = m0 ^ m1
        tt.append(y0 | (y1 << 1))

    ok = verify_circuit(qc2, tt)
    assert ok, "Verification failed!"
    print("[PASS] truth table verification\n")

    print("=== All tests passed ===")
