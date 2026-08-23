# coding: utf-8
"""
Classical Circuit Parser
Replaces extract_linear() from classical_to_quantum.sage.

Parses string-based classical circuit descriptions into linear expressions
grouped by AND-depth layer, using pure Python (no SageMath).

Circuit string format:
  XOR : "T1=X0+X3"   (two-input XOR over GF(2))
  NOT : "Y0=Y0+1"    (add constant 1, equivalent to bitwise NOT)
  AND : "M1=T1*T2"   (two-input AND gate, introduces a new M symbol)

Inputs  must be named X0, X1, ...
Outputs must be named Y0, Y1, ...
"""

from gf2_matrix import GF2Matrix


def _expr_to_str(expr_set: frozenset) -> str:
    """
    Convert a frozenset of GF(2) basis variable names to a '+'-joined string.
    Ordering: X variables first, then M variables, then constant '1'.
    """
    if not expr_set:
        return "0"
    terms = sorted(expr_set,
                   key=lambda x: (x == "1", x.startswith("M"), x))
    return "+".join(terms)


def parse_circuit(n: int, m: int, C: list):
    """
    Parse classical circuit and extract linear expressions by AND-depth layer.

    Parameters
    ----------
    n : int
        Number of input variables (X0 .. Xn-1).
    m : int
        Number of output variables (Y0 .. Ym-1).
    C : list of str
        Circuit operations in topological order, e.g.
        ["T1=X0+X3", "M0=T1*T2", "Y0=M0+X1"].

    Returns
    -------
    L : list of (AND_depth + 2) sublists
        L[0]   = ["X0", "X1", ..., "Xn-1"]  (initial inputs)
        L[d]   = affine expression strings for the two inputs of each AND gate
                 at depth d, ordered as [D1_1, D1_2, D2_1, D2_2, ...]
        L[-1]  = affine expression strings for outputs Y0 .. Ym-1
    AND_depth : int
        Total AND-depth s of the circuit.
    total_M : int
        Total number of AND gates (= number of M symbols introduced).
    """

    # ------------------------------------------------------------------ #
    # Pass 1 — compute AND-depth of every variable; collect AND gates
    # ------------------------------------------------------------------ #
    vars_depth = {"1": 0}
    for i in range(n):
        vars_depth[f"X{i}"] = 0

    AND_depth = 0
    AND_depth_layer = [[]]   # AND_depth_layer[d] = list of circuit-var names at depth d
    AND_inputs = {}           # circuit_var -> [left_input_name, right_input_name]

    for oper in C:
        oper = oper.replace(" ", "")
        lhs, rhs = oper.split("=", 1)

        if "*" in rhs:                                       # AND gate
            a, b = rhs.split("*", 1)
            d = 1 + max(vars_depth.get(a, 0), vars_depth.get(b, 0))
            vars_depth[lhs] = d
            AND_depth = max(AND_depth, d)
            while len(AND_depth_layer) <= d:
                AND_depth_layer.append([])
            AND_depth_layer[d].append(lhs)
            AND_inputs[lhs] = [a, b]

        elif "+" in rhs:                                     # XOR / NOT
            a, b = rhs.split("+", 1)
            vars_depth[lhs] = max(vars_depth.get(a, 0),
                                  vars_depth.get(b, 0))

        else:                                                # direct assignment
            vars_depth[lhs] = vars_depth.get(rhs, 0)

    # ------------------------------------------------------------------ #
    # Assign M symbols to AND gate outputs, ordered by AND-depth layer
    # (matches the reordering in the original SageMath code)
    # ------------------------------------------------------------------ #
    var_to_sym: dict = {"1": frozenset(["1"])}
    for i in range(n):
        var_to_sym[f"X{i}"] = frozenset([f"X{i}"])

    M_idx = 0
    for d in range(1, AND_depth + 1):
        for v in AND_depth_layer[d]:
            var_to_sym[v] = frozenset([f"M{M_idx}"])
            M_idx += 1

    total_M = M_idx

    # ------------------------------------------------------------------ #
    # Pass 2 — evaluate XOR operations in circuit order
    # AND outputs already carry their M symbol; skip those lines.
    # ------------------------------------------------------------------ #
    for oper in C:
        oper = oper.replace(" ", "")
        lhs, rhs = oper.split("=", 1)

        if "*" in rhs:
            continue

        if "+" in rhs:
            a, b = rhs.split("+", 1)
            sym_a = var_to_sym.get(a, frozenset([a]))
            sym_b = var_to_sym.get(b, frozenset([b]))
            var_to_sym[lhs] = sym_a.symmetric_difference(sym_b)
        else:
            var_to_sym[lhs] = var_to_sym.get(rhs, frozenset([rhs]))

    # ------------------------------------------------------------------ #
    # Build output L
    # ------------------------------------------------------------------ #
    L = [[] for _ in range(AND_depth + 2)]
    L[0] = [f"X{i}" for i in range(n)]

    for d in range(1, AND_depth + 1):
        for v in AND_depth_layer[d]:
            inp1, inp2 = AND_inputs[v]
            e1 = _expr_to_str(var_to_sym.get(inp1, frozenset([inp1])))
            e2 = _expr_to_str(var_to_sym.get(inp2, frozenset([inp2])))
            L[d].append(e1)
            L[d].append(e2)

    for i in range(m):
        sym = var_to_sym.get(f"Y{i}", frozenset([f"Y{i}"]))
        L[-1].append(_expr_to_str(sym))

    return L, AND_depth, total_M


def linears_to_matrix(L: list, n: int, cols: int) -> GF2Matrix:
    """
    Convert a list of affine expression strings to a GF(2) matrix.

    Parameters
    ----------
    L    : list of str, e.g. ["X0+M1", "X2"]
    n    : number of X input variables
    cols : total columns = n + (number of M variables visible so far)

    Returns
    -------
    GF2Matrix of shape (len(L), cols)
    """
    vars_to_idx = {}
    for i in range(n):
        vars_to_idx[f"X{i}"] = i
    for i in range(cols - n):
        vars_to_idx[f"M{i}"] = n + i

    rows = len(L)
    data = [[0] * cols for _ in range(rows)]

    for i, expr_str in enumerate(L):
        if expr_str in ("0", ""):
            continue
        for term in expr_str.split("+"):
            if term in vars_to_idx:
                data[i][vars_to_idx[term]] ^= 1   # GF(2) add

    return GF2Matrix(data)


# ------------------------------------------------------------------ #
# Self-test
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    print("=== linear_parser self-test ===\n")

    # ---- Test 1: simple 4-input, 2-output, AND-depth-2 circuit ----
    n, m = 4, 2
    C = [
        "T1=X0+X1",   # XOR
        "T2=X2+X3",   # XOR
        "M0=T1*T2",   # AND depth 1 → symbol M0
        "T3=X0+M0",   # XOR uses AND output
        "T4=X1+X2",   # XOR
        "M1=T3*T4",   # AND depth 2 → symbol M1
        "Y0=X0+M1",   # output Y0
        "Y1=M0+M1",   # output Y1
    ]

    L, s, total_M = parse_circuit(n=n, m=m, C=C)

    print(f"AND-depth   s = {s}  (expected 2)")
    print(f"Total AND gates = {total_M}  (expected 2)")
    print(f"\nL[0] (inputs)      : {L[0]}")
    print(f"L[1] (AND-1 inputs): {L[1]}")
    print(f"L[2] (AND-2 inputs): {L[2]}")
    print(f"L[3] (outputs Y)   : {L[3]}")

    assert s == 2
    assert total_M == 2
    assert L[1] == ["X0+X1", "X2+X3"],   f"L[1] wrong: {L[1]}"
    assert L[2] == ["X0+M0", "X1+X2"],   f"L[2] wrong: {L[2]}"
    assert L[3] == ["X0+M1", "M0+M1"],   f"L[3] wrong: {L[3]}"
    print("\n[PASS] parse_circuit")

    # ---- Test 2: linears_to_matrix ----
    # L[1]: inputs of AND depth-1 gates; at this point only X variables exist → cols=4
    mat1 = linears_to_matrix(L[1], n=4, cols=4)
    print(f"\nlinears_to_matrix(L[1], cols=4):\n{mat1}")
    assert mat1.data == [[1, 1, 0, 0],
                         [0, 0, 1, 1]], f"mat1 wrong: {mat1.data}"

    # L[2]: inputs of AND depth-2 gates; M0 now exists → cols=5
    mat2 = linears_to_matrix(L[2], n=4, cols=5)
    print(f"\nlinears_to_matrix(L[2], cols=5):\n{mat2}")
    assert mat2.data == [[1, 0, 0, 0, 1],
                         [0, 1, 1, 0, 0]], f"mat2 wrong: {mat2.data}"
    print("\n[PASS] linears_to_matrix")

    # ---- Test 3: NOT gate (constant 1 in output) ----
    C3 = [
        "T1=X0+X1",
        "M0=T1*X2",
        "Y0=M0+X3",
        "Y0=Y0+1",       # NOT: Y0 gets flipped
    ]
    L3, s3, _ = parse_circuit(n=3, m=1, C=C3)
    print(f"\nNOT gate test: L3[-1] = {L3[-1]}")
    assert "1" in L3[-1][0], f"Constant '1' missing: {L3[-1]}"
    print("[PASS] NOT gate")

    # ---- Test 4: rank check via linears_to_matrix ----
    # mat1 has rank 2 (two independent rows)
    assert mat1.rank() == 2, f"rank wrong: {mat1.rank()}"
    print("\n[PASS] rank check")

    print("\n=== All tests passed ===")
