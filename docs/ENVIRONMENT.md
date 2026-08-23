# Recorded environments and bounded-search parameters

The artifact records only environment facts captured from the execution hosts;
no hardware value is reconstructed or guessed.

## Primary bounded AND search

- operating system: Windows 11 x86-64;
- Python: 3.12.13;
- Z3: 4.16.0;
- default seed: 0;
- primary timeout: 60,000 ms per solver call;
- longer unresolved-instance retries: 300,000 ms at seed 1 and 600,000 ms at
  seed 2;
- search range: increasing total AND count with all admitted `k1/k2`
  partitions, bounded by the per-S-box `k_max` recorded in the solver tables;
- recorded per attempt: status, elapsed seconds, constraints, SMT2 bytes,
  timeout, seed, and truth-table result when SAT.

## Linux extended benchmarks

- platform: Linux 6.8 x86-64 with glibc 2.35 (Ubuntu 22.04 generation);
- Python: 3.13.5;
- Z3: 4.15.4;
- CPU: two Intel(R) Xeon(R) Platinum 8352V processors at 2.10 GHz;
- topology: 2 sockets, 36 physical cores per socket, 2 threads per core, and
  144 logical CPUs;
- available memory at execution: 125 GiB RAM;
- seeds: 0, 1, 2;
- `k_min=0`, `k_max=8`;
- timeout: 10,800,000 ms per check;
- process-level jobs: 15.

## LIGHTER-R rerun

- upstream commit: `146608220e30e47a4521947933b618e20f53f624`;
- compiler: GNU g++ 11.4.0;
- platform and hardware pool: same Linux host described above;
- primary jobs: 6;
- extended jobs: 5;
- OpenMP threads per job: 8;
- RAM-bound parameter: 20;
- lambda bound: 200;
- timeout: 10,800 seconds per S-box;
- objective configuration: `0.01 X + 1 CNOT + 7 CCNOT`;
- allowed gate library: X, CNOT, CCNOT; no higher-control Toffoli;
- logical input/output wire assignments: free;
- ancilla limit: zero for the in-place search.

The machine username, IP address, absolute binary path, and local working
directory were removed because they are irrelevant to reproducibility and
would compromise anonymous review.
