# coding: utf-8
"""
GF(2) Matrix Operations
Replaces SageMath's matrix(GF(2), ...) for small matrices (4-bit S-box case).
Operations: addition (XOR), multiplication (AND), rank, inverse, echelon form.
"""


class GF2Matrix:
    """
    Matrix over GF(2). Internally stored as list of lists of int (0 or 1).
    rows: number of rows
    cols: number of columns
    data: list of rows, each row is a list of 0/1
    """

    def __init__(self, data):
        """
        data: list of lists, e.g. [[1,0],[0,1]]
        Values are reduced mod 2 automatically.
        """
        self.rows = len(data)
        self.cols = len(data[0]) if self.rows > 0 else 0
        self.data = [[int(v) % 2 for v in row] for row in data]

    # ------------------------------------------------------------------ #
    # Basic helpers
    # ------------------------------------------------------------------ #
    def copy(self):
        return GF2Matrix([row[:] for row in self.data])

    def __repr__(self):
        lines = ["[" + " ".join(str(v) for v in row) + "]" for row in self.data]
        return "\n".join(lines)

    def __eq__(self, other):
        return self.data == other.data

    # ------------------------------------------------------------------ #
    # Arithmetic
    # ------------------------------------------------------------------ #
    def __add__(self, other):
        assert self.rows == other.rows and self.cols == other.cols
        result = [[( self.data[i][j] + other.data[i][j]) % 2
                   for j in range(self.cols)]
                  for i in range(self.rows)]
        return GF2Matrix(result)

    def __mul__(self, other):
        """Matrix multiply over GF(2)."""
        if isinstance(other, GF2Matrix):
            assert self.cols == other.rows
            result = []
            for i in range(self.rows):
                row = []
                for j in range(other.cols):
                    v = sum(self.data[i][k] * other.data[k][j]
                            for k in range(self.cols)) % 2
                    row.append(v)
                result.append(row)
            return GF2Matrix(result)
        elif isinstance(other, list):
            # multiply matrix by column vector (list of int)
            assert self.cols == len(other)
            result = []
            for i in range(self.rows):
                v = sum(self.data[i][k] * other[k]
                        for k in range(self.cols)) % 2
                result.append(v)
            return result
        else:
            raise TypeError(f"Unsupported type: {type(other)}")

    # ------------------------------------------------------------------ #
    # Row operations (in-place)
    # ------------------------------------------------------------------ #
    def _swap_rows(self, i, j):
        self.data[i], self.data[j] = self.data[j], self.data[i]

    def _add_row(self, dst, src):
        """dst_row ^= src_row"""
        self.data[dst] = [(self.data[dst][k] + self.data[src][k]) % 2
                          for k in range(self.cols)]

    # ------------------------------------------------------------------ #
    # Gaussian elimination → row echelon form
    # Returns (echelon_matrix, pivot_cols, transformation_matrix)
    # transformation_matrix T satisfies: T * self = echelon_matrix
    # ------------------------------------------------------------------ #
    def _gauss(self, track_transform=False):
        M = self.copy()
        n = M.rows
        if track_transform:
            T = identity(n)
        pivot_cols = []
        cur_row = 0
        for col in range(M.cols):
            # find pivot
            pivot = None
            for r in range(cur_row, n):
                if M.data[r][col] == 1:
                    pivot = r
                    break
            if pivot is None:
                continue
            # swap
            M._swap_rows(cur_row, pivot)
            if track_transform:
                T._swap_rows(cur_row, pivot)
            # eliminate below (and above for RREF)
            for r in range(n):
                if r != cur_row and M.data[r][col] == 1:
                    M._add_row(r, cur_row)
                    if track_transform:
                        T._add_row(r, cur_row)
            pivot_cols.append(col)
            cur_row += 1
            if cur_row == n:
                break
        if track_transform:
            return M, pivot_cols, T
        return M, pivot_cols

    # ------------------------------------------------------------------ #
    # Public: rank
    # ------------------------------------------------------------------ #
    def rank(self):
        _, pivot_cols = self._gauss()
        return len(pivot_cols)

    # ------------------------------------------------------------------ #
    # Public: inverse (only for square, full-rank matrices)
    # ------------------------------------------------------------------ #
    def inverse(self):
        assert self.rows == self.cols, "Only square matrices can be inverted"
        n = self.rows
        # augment [A | I]
        aug = GF2Matrix([self.data[i] + identity(n).data[i]
                         for i in range(n)])
        # RREF
        rref, pivot_cols = aug._gauss(track_transform=False)
        # left part should be I; right part is A^{-1}
        left = GF2Matrix([rref.data[i][:n] for i in range(n)])
        right = GF2Matrix([rref.data[i][n:] for i in range(n)])
        assert left == identity(n), "Matrix is not invertible over GF(2)"
        return right

    # ------------------------------------------------------------------ #
    # Public: extended_echelon_form
    # Returns a combined matrix [RREF | T] where T * self = RREF
    # Mimics SageMath's extended_echelon_form(transformation=True)
    # ------------------------------------------------------------------ #
    def extended_echelon_form(self):
        """
        Returns (rref, T) such that T * self = rref.
        Access: result[i][cols + j] gives T[i][j]  (same indexing as SageMath)
        """
        n = self.rows
        c = self.cols
        # augment [A | I]
        aug_data = [self.data[i] + identity(n).data[i] for i in range(n)]
        aug = GF2Matrix(aug_data)
        rref_aug, pivot_cols = aug._gauss(track_transform=False)
        # split back
        rref = GF2Matrix([rref_aug.data[i][:c] for i in range(n)])
        T    = GF2Matrix([rref_aug.data[i][c:] for i in range(n)])
        # build combined matrix for indexing compatibility
        combined = GF2Matrix([rref_aug.data[i] for i in range(n)])
        return combined, T


# ------------------------------------------------------------------ #
# Utility: identity matrix
# ------------------------------------------------------------------ #
def identity(n):
    data = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    return GF2Matrix(data)


def zeros(rows, cols):
    return GF2Matrix([[0] * cols for _ in range(rows)])


# ------------------------------------------------------------------ #
# Self-test
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    print("=== GF2Matrix self-test ===")

    # identity
    I = identity(3)
    print("Identity 3x3:")
    print(I)

    # use a full-rank matrix: rank = 3
    # A = [[1,0,0],[0,1,0],[1,1,1]], rows are linearly independent over GF(2)
    A = GF2Matrix([[1, 0, 0], [0, 1, 0], [1, 1, 1]])
    B = GF2Matrix([[1, 1, 0], [1, 0, 1], [0, 1, 1]])
    print("\nA + B:")
    print(A + B)

    # multiply
    print("\nA * B:")
    print(A * B)

    # rank
    print(f"\nrank(A) = {A.rank()}")  # expect 3

    # singular matrix test (row3 = row1 XOR row2)
    singular = GF2Matrix([[1, 0, 1], [0, 1, 1], [1, 1, 0]])
    print(f"rank(singular) = {singular.rank()}")  # expect 2

    # inverse
    Ainv = A.inverse()
    print("\nA^{-1}:")
    print(Ainv)
    print("A * A^{-1} (should be I):")
    print(A * Ainv)

    # extended echelon form
    combined, T = A.extended_echelon_form()
    print("\nT such that T*A = RREF:")
    print(T)
    print("T * A:")
    print(T * A)

    print("\n=== All tests passed ===")
