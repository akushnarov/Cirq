# Cirq Fundamental Operations Optimization: Implementation Tasks & Execution Plan (TASKS.md)

This document specifies the granular, phased implementation tasks for optimizing Cirq's fundamental operations to scale to $O(1000)$ qubits and $10^6+$ operations.

---

## 🐙 Git Merge & Fork Target Rule

> [!IMPORTANT]
> **CRITICAL REPOSITORY RULE**: **All PRs, feature branches, and merges MUST target the Fork (`origin/main` / `git@github.com:akushnarov/Cirq.git`). NEVER merge or push directly to the upstream Cirq repository (`upstream/main` / `quantumlib/Cirq`). Upstream is strictly read-only for fetching updates.**

---

## 🔄 Standardized Task Execution Routine

Every task executed by an agent or developer MUST follow this strict 7-step lifecycle:

$$\begin{aligned}
\text{Step 1: Create Feature Branch (from origin/main)} &\longrightarrow \text{Step 2: Do Changes (Implementation)} \\
&\longrightarrow \text{Step 3: Run Tests, Linting \& Quality Checks} \\
&\longrightarrow \text{Step 4: Run Related Benchmarks} \\
&\longrightarrow \text{Step 5: Track Improvement + Save Exact Commit/Branch Association} \\
&\longrightarrow \text{Step 6: Commit \& Merge ONLY to Fork (origin/main)} \\
&\longrightarrow \text{Step 7: Mark Task Finished in TASKS.md} \longrightarrow \text{Next Task}
\end{aligned}$$

### Detailed Step Protocol:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b <branch_name> origin/main
   ```
2. **Do Changes (Implementation)**: Modify the target files according to task specifications, adhering to `@cirq.value.value_equality` immutability and slotted architecture.
3. **Run Tests, Linting & Quality Checks (Strict Verification Suite)**:
   Every change must pass the complete verification suite before moving to benchmarking or merging:
   - **Targeted Unit Tests**:
     ```bash
     pytest <test_paths> -v
     ```
   - **Changed-Files Fast Pytest**:
     ```bash
     ./check/pytest-changed-files origin/main
     ```
   - **Incremental Code Formatting (Ruff, Black, isort)**:
     ```bash
     ./check/format-incremental origin/main --apply
     ```
   - **Pylint Linting on Changed Files**:
     ```bash
     ./check/pylint-changed-files origin/main
     ```
   - **Static Type Checking (Mypy)**:
     ```bash
     ./check/typecheck
     ```
   - **Repository Hygiene & Formatting Checks**:
     ```bash
     ./check/misc
     ```
   - **Native Rust Verification (for Phase 2 native modules)**:
     ```bash
     cargo test --workspace
     cargo clippy --workspace --all-targets -- -D warnings
     cargo fmt --check
     ```
4. **Run Related Benchmarks**: Execute the targeted benchmark script and memory profiler.
5. **Track Improvement & Associate Specific Commit**:
   - Record the exact branch name and commit hash alongside the benchmark metrics.
   - Format: Write JSON tracking record to `benchmarks/tracking/<task_id>_<commit_sha>.json`:
     ```json
     {
       "task_id": "Task 1.X",
       "branch": "<branch_name>",
       "commit_sha": "<git_rev_parse_HEAD>",
       "timestamp": "2026-08-20T...",
       "metrics": {
         "latency_ns": 0.0,
         "throughput_ops_per_sec": 0.0,
         "memory_mb": 0.0,
         "speedup_vs_baseline": "X.X x"
       }
     }
     ```
   - This ensures specific commits can be verified, audited, selected, or cherry-picked.
6. **Pre-Merge CI Validation & Commit/Merge to Fork**:
   - **MANDATORY CI CHECK**: Before committing and merging, execute the complete CI parity check suite to guarantee 100% pass rate on GitHub Actions ([.github/workflows/ci.yml](file:///usr/local/google/home/andriyku/workspace/Cirq/.github/workflows/ci.yml)):
     ```bash
     # Single command verifying all changed-files CI jobs
     ./check/all --changed origin/main
     ```
   - Verify that `./check/all --changed origin/main` exits with `All checks passed.` (code 0).
   - Create signed commit:
     ```bash
     git commit -S -m "<type>(<scope>): <description>"
     ```
   - Merge ONLY to Fork (`origin/main`):
     ```bash
     git checkout main
     git pull origin main
     git merge --ff-only <branch_name>
     git push origin main
     ```
7. **Mark Task as Finished in TASKS.md**:
   - Update the task's status line in `TASKS.md` to `- **Status**: [x] Completed (Commit: <commit_sha>)`.
   - Record the verified metrics summary under the task.
   - Advance to the next task in the dependency graph.

---

## 🛡️ Pre-Merge GitHub Actions CI Equivalence Gate (.github/workflows/ci.yml)

To guarantee that any feature branch merged into the Fork (`origin/main`) passes GitHub Actions Continuous Integration identically to upstream CI, developers and agents MUST verify against the following local job mappings:

| CI Workflow Job (`ci.yml`) | Local Equivalence Command | Description |
| :--- | :--- | :--- |
| **`quick_test`** | `./check/misc` | License headers, non-contrib imports, whitespace hygiene |
| **`format`** | `./check/format-incremental origin/main --apply` | Incremental code formatting (Ruff, Black, isort) |
| **`lint`** | `ruff check` && `./check/pylint-changed-files origin/main` | Static analysis with Ruff and Pylint |
| **`typecheck`** | `FORCE_COLOR=1 ./check/typecheck` | Static type checking with Mypy |
| **`changed_files`** | `./check/pytest-changed-files origin/main -n logical` | Fast pytest on all modified modules |
| **`pytest`** | `pytest <test_paths> -v` | Targeted subsystem unit tests |
| **`coverage`** | `./check/pytest-changed-files-and-incremental-coverage origin/main` | Incremental test coverage guard |
| **`doc_test`** | `./check/doctest -q` | Docstring doctests |
| **`build_protos`** | `./check/protos-up-to-date` | Protobuf definitions consistency |
| **`shellcheck`** | `./check/shellcheck` | Bash scripts validation |
| **Fast CI Suite** | `./check/all --changed origin/main` | **Single-command runner executing the complete changed-files CI pipeline** |

---

## ⚡ Parallel Subagent Concurrency Matrix

To maximize throughput, tasks that touch **disjoint code modules** can be executed concurrently in parallel subagents without merge conflicts:

| Execution Wave | Parallel Subagent Track | Assigned Task & Scope | Target Files (Disjoint Module Scope) | Can Run in Parallel With |
| :--- | :--- | :--- | :--- | :--- |
| **Wave 1** | **Track A1 (Core Hierarchy)** | **Task 1.1**: Universal `__slots__` on Qubits/Gates/Ops | `cirq-core/cirq/ops/`, `devices/` | Tasks 1.7, 1.9 |
| **Wave 1** | **Track B1 (Routing / Graph)** | **Task 1.7**: SciPy Shortest Path in `MappingManager` | `cirq-core/cirq/transformers/routing/` | Tasks 1.1, 1.9 |
| **Wave 1** | **Track C1 (Protocols)** | **Task 1.9**: Eliminate `inspect.signature` in `decompose` | `cirq-core/cirq/protocols/` | Tasks 1.1, 1.7 |
| **Wave 2** | **Track A2 (Values & Equality)**| **Task 1.2**: Slotted Method Caching & Fast Equality | `cirq-core/cirq/value/`, `cirq/_compat.py` | Tasks 1.3, 1.5 |
| **Wave 2** | **Track B2 (Moment Engine)** | **Task 1.3**: Bitmask Moment Collision Engine | `cirq-core/cirq/circuits/moment.py` | Tasks 1.2, 1.5 |
| **Wave 2** | **Track C2 (Circuit DAG)** | **Task 1.5**: Linear-Time $O(N)$ `CircuitDag` | `cirq-core/cirq/circuits/circuit_dag.py` | Tasks 1.2, 1.3 |
| **Wave 3** | **Track A3 (Circuit Append)** | **Task 1.4**: Fast Layer Append & Placement Cache | `cirq-core/cirq/circuits/circuit.py` | Tasks 1.6, 1.8 |
| **Wave 3** | **Track B3 (Transformers)** | **Task 1.8**: Batch Insertion in `align_left/right` | `cirq-core/cirq/transformers/align_*.py` | Tasks 1.4, 1.6 |
| **Wave 3** | **Track C3 (Parameter Sweep)**| **Task 1.6**: Topology-Invariant Parameter Resolution | `cirq-core/cirq/protocols/resolve_parameters.py` | Tasks 1.4, 1.8 |
| **Wave 4** | **Track D (QEC Synthesis)** | **Task 1.10**: Vectorized Surface Code & QEC Generator | `benchmarks/`, `cirq/experiments/` | End of Phase 1 |
| **Phase 2** | **Track Rust Core** | **Tasks 2.1 – 2.5**: `PackedOp` Arena & SIMD BitVec | `crates/cirq-core-rs/` | Pure Rust workspace |
| **Phase 2** | **Track Rust Passes** | **Tasks 2.6 – 2.7**: Native Passes & Stim Bridge | `crates/cirq-core-rs/src/transformers/` | Independent pass modules |

---

## 1. Task Dependency Graph

```mermaid
graph TD
    subgraph "Wave 1: Parallel Independent Tasks"
        T1_1["[PARALLEL 1A] Task 1.1: Universal __slots__ Hierarchy"]
        T1_7["[PARALLEL 1B] Task 1.7: SciPy Shortest Path in MappingManager"]
        T1_9["[PARALLEL 1C] Task 1.9: Eliminate inspect.signature in Decompose"]
    end

    subgraph "Wave 2: Parallel Post-Slots Tasks"
        T1_2["[PARALLEL 2A] Task 1.2: Slotted Caching & Fast Equality"]
        T1_3["[PARALLEL 2B] Task 1.3: Bitmask Moment Collision Engine"]
        T1_5["[PARALLEL 2C] Task 1.5: Linear-Time CircuitDag Construction"]
    end

    subgraph "Wave 3: Parallel Post-Moment Tasks"
        T1_4["[PARALLEL 3A] Task 1.4: Fast Layer Append & Placement Cache"]
        T1_6["[PARALLEL 3B] Task 1.6: Topology-Invariant Parameter Resolution"]
        T1_8["[PARALLEL 3C] Task 1.8: Batch Insertion in align_left/right"]
    end

    subgraph "Wave 4: QEC Workload Synthesis"
        T1_10["[PARALLEL 4] Task 1.10: Vectorized Surface Code Generator"]
    end

    T1_1 --> T1_2
    T1_1 --> T1_3
    T1_1 --> T1_5
    T1_3 --> T1_4
    T1_3 --> T1_6
    T1_3 --> T1_8
    T1_4 --> T1_10

    subgraph "Phase 2: Native Rust Hybrid Core cirq_core_rs"
        T2_1[Task 2.1: Rust Workspace Scaffolding] --> T2_2[Task 2.2: QubitRegistry & Interning]
        T2_2 --> T2_3[Task 2.3: PackedOp Arena & StandardGate Enum]
        T2_3 --> T2_4[Task 2.4: SIMD BitVec Moment Collision Engine]
        T2_4 --> T2_5[Task 2.5: Native CircuitData & Lazy MomentView]
        T2_5 --> T2_6["[PARALLEL 2.6] Task 2.6: Native Transpilation Passes"]
        T2_5 --> T2_7["[PARALLEL 2.7] Task 2.7: Native RepeatBlock AST & Stim Bridge"]
    end

    Wave 4 --> Phase 2
```

---

## 2. Phase 1: Pure Python 3.13 Fast-Path Optimization

### Task 1.1: Universal `__slots__` Adoption on Core Classes `[WAVE 1 - TRACK A1: PARALLEL]`
- **Status**: `[x] Completed (Commit: 9e5b49456661fe1c0bcf5364691bfbfbaad00693)`
- **Priority**: `P0`
- **Estimated Effort**: 1-2 days
- **Concurrency**: **Can run concurrently with Task 1.7 and Task 1.9**
- **Dependencies**: None
- **Target Files**:
  - `cirq-core/cirq/ops/raw_types.py` (`Operation`, `GateOperation`, `TaggedOperation`)
  - `cirq-core/cirq/devices/line_qubit.py` (`LineQubit`, `LineQid`)
  - `cirq-core/cirq/devices/grid_qubit.py` (`GridQubit`, `GridQid`)
  - `cirq-core/cirq/devices/named_qubit.py` (`NamedQubit`, `NamedQid`)
  - `cirq-core/cirq/circuits/moment.py` (`Moment`)
  - `cirq-core/cirq/circuits/circuit.py` (`Circuit`, `_PlacementCache`)
- **Verified Benchmark Results**:
  - **Memory Footprint**: 1,000,000 Operations (1,000 Qubits $\times$ 1,000 Moments) peak memory dropped from **448.66 MB** to **150.15 MB** (**66.5% memory reduction** / 3.0x memory efficiency).
  - **Construction Latency**: 1M ops construction time dropped from **36.31 s** to **10.80 s** (**3.36x speedup** / 92,561 ops/sec throughput).
  - **Slotted Object Verification**: `hasattr(obj, '__dict__') is False` verified across all core types (`GridQubit`, `LineQubit`, `NamedQubit`, `GateOperation`, `TaggedOperation`, `Moment`, `Circuit`).
  - **Tracking Record**: `benchmarks/tracking/task_1_1_9e5b49456661fe1c0bcf5364691bfbfbaad00693.json`.

---

### Task 1.7: SciPy Compiled Shortest Paths in `MappingManager` `[WAVE 1 - TRACK B1: PARALLEL]`
- **Status**: `[x] Completed (Commit: 544187bd0622231bdc4b1ebb30c94dda3b69dfbf)`
- **Priority**: `P0`
- **Estimated Effort**: 0.5 day
- **Concurrency**: **Can run concurrently with Task 1.1 and Task 1.9 (Fully Disjoint Module)**
- **Dependencies**: None
- **Target Files**:
  - `cirq-core/cirq/transformers/routing/mapping_manager.py` (`MappingManager.__init__`)
- **Verified Benchmark Speedup**:
  - Baseline Latency ($N=1000$ Grid): `106.99 s`
  - Optimized Latency ($N=1000$ Grid): `0.0981 s`
  - **Speedup**: **1,090x**
  - **Test Suite**: 77/77 passed (100% incremental coverage)
  - **Tracking Record**: `benchmarks/tracking/task_1_7_544187bd0622231bdc4b1ebb30c94dda3b69dfbf.json`

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-scipy-routing-init origin/main
   ```
2. **Do Changes (Implementation)**:
   - Replace NetworkX's pure-Python `nx.floyd_warshall_predecessor_and_distance` with `scipy.sparse.csgraph.shortest_path(adj_matrix, directed=False)`.
   - Build the adjacency matrix using `scipy.sparse.csr_matrix` from device topology edges.
3. **Run Tests, Linting & Format Checks**:
   ```bash
   pytest cirq-core/cirq/transformers/routing/ -v
   ./check/pytest-changed-files origin/main
   ./check/format-incremental origin/main --apply
   ./check/pylint-changed-files origin/main
   ./check/typecheck
   ./check/misc
   ```
4. **Run Related Benchmarks**:
   ```bash
   python -c "import networkx as nx, cirq, time; g=nx.grid_2d_graph(50, 20); cm=cirq.transformers.routing.mapping_manager.MappingManager; t0=time.perf_counter(); m=cm(g); print('Routing init N=1000:', time.perf_counter()-t0, 's')"
   ```
5. **Track Improvement & Save Commit Association**:
   - Target Metric: 1,000-qubit grid initialization drops from **106.99 seconds** to **< 0.10 seconds (>1,000x speedup)**.
   - Record exact commit and metrics in `benchmarks/tracking/task_1_7_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "perf(routing): compiled scipy csgraph shortest path for MappingManager initialization"
   git checkout main && git pull origin main && git merge --ff-only perf-scipy-routing-init && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 1.9: Eliminate `inspect.signature` in `decompose` DFS & Fast-Path Protocol Lookups `[WAVE 1 - TRACK C1: PARALLEL]`
- **Status**: `[x] Completed (Commit: d8b99c94a7802e646329dffa24a6de4bce3ff874)`
- **Priority**: `P1`
- **Estimated Effort**: 1-2 days
- **Concurrency**: **Can run concurrently with Task 1.1 and Task 1.7 (Fully Disjoint Module)**
- **Dependencies**: None
- **Target Files**:
  - `cirq-core/cirq/protocols/decompose_protocol.py` (`_decompose_dfs`, `_try_op_decomposer`)
  - `cirq-core/cirq/protocols/unitary_protocol.py` (`unitary`, `has_unitary`)
  - `cirq-core/cirq/ops/op_tree.py` (`flatten_to_ops`)
- **Verified Benchmark Speedup**:
  - `cirq.decompose` Latency (50k SWAPs / 224k ops): **3.230 s $\to$ 2.174 s** (103,309 ops/sec throughput, 1.49x speedup)
  - `cirq.has_unitary` Latency (100k calls): **0.0576 s** (1,735,130 ops/sec throughput)
  - `cirq.unitary` Latency (100k calls): **0.9445 s** (105,876 ops/sec throughput)
  - **Test Suite**: 170/170 passed (100% incremental coverage)
  - **Tracking Record**: `benchmarks/tracking/task_1_9_d8b99c94a7802e646329dffa24a6de4bce3ff874.json`

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-fast-decompose origin/main
   ```
2. **Do Changes (Implementation)**:
   - Replace dynamic `inspect.signature(decomposer).parameters` in `_try_op_decomposer` with an attribute flag `getattr(decomposer, '_accepts_context', False)` or explicit protocol check.
   - Add an internal `_IS_CIRCUIT_BUILTIN = True` flag on standard gates (`X`, `Y`, `Z`, `H`, `CZ`, `CNOT`, `PhasedXZ`, `FSim`) to fast-path `cirq.unitary` directly to `gate._unitary_()` without entering the fallback ladder.
3. **Run Tests, Linting & Format Checks**:
   ```bash
   pytest cirq-core/cirq/protocols/decompose_protocol_test.py cirq-core/cirq/protocols/unitary_protocol_test.py -v
   ./check/pytest-changed-files origin/main
   ./check/format-incremental origin/main --apply
   ./check/pylint-changed-files origin/main
   ./check/typecheck
   ./check/misc
   ```
4. **Run Related Benchmarks**:
   ```bash
   python -c "import cirq, time; qs=[cirq.LineQubit(i) for i in range(1000)]; c=cirq.Circuit(cirq.SWAP(qs[i], qs[i+1]) for i in range(0, 998, 2) for _ in range(50)); t0=time.perf_counter(); cirq.decompose(c); print('Decompose 50k SWAPs:', time.perf_counter()-t0, 's')"
   ```
5. **Track Improvement & Save Commit Association**:
   - Target Metric: `cirq.decompose` on 50k composite gates drops from **3.52s** to **< 0.80s (4.4x speedup)**.
   - Record exact commit and metrics in `benchmarks/tracking/task_1_9_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "perf(protocols): eliminate inspect.signature introspection and add builtin gate protocol fast paths"
   git checkout main && git pull origin main && git merge --ff-only perf-fast-decompose && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 1.2: Slotted Method Caching & Fast-Path Value Equality `[WAVE 2 - TRACK A2: PARALLEL]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P0`
- **Estimated Effort**: 1 day
- **Concurrency**: **Can run concurrently with Task 1.3 and Task 1.5**
- **Dependencies**: Task 1.1
- **Target Files**:
  - `cirq-core/cirq/_compat.py` (`cached_method`, `cached_property`)
  - `cirq-core/cirq/value/value_equality_attr.py` (`value_equality`)
  - `cirq-core/cirq/ops/gate_operation.py` (`GateOperation.__eq__`)
  - `cirq-core/cirq/ops/common_gates.py` (`_group_interchangeable_qubits`)

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-fast-equality origin/main
   ```
2. **Do Changes (Implementation)**:
   - Refactor `cached_method` to store cached values in explicit private slot attributes (e.g. `_cached_value_equality_values`) rather than injecting into dynamic `__dict__`.
   - Implement an inlined fast-path equality in `GateOperation.__eq__`:
     ```python
     if self is other:
         return True
     if type(self) is type(other):
         return self._gate == other._gate and self._qubits == other._qubits
     ```
   - Optimize `_group_interchangeable_qubits` to avoid intermediate set and dictionary allocation for 2-qubit symmetric gates (`CZ`, `SWAP`).
3. **Run Tests, Linting & Format Checks**:
   ```bash
   pytest cirq-core/cirq/value/ cirq-core/cirq/ops/ -v
   ./check/pytest-changed-files origin/main
   ./check/format-incremental origin/main --apply
   ./check/pylint-changed-files origin/main
   ./check/typecheck
   ./check/misc
   ```
4. **Run Related Benchmarks**:
   ```bash
   python -c "import cirq, timeit; q=cirq.LineQubit(0); op1=cirq.X(q); op2=cirq.X(q); print('Eq latency:', timeit.timeit(lambda: op1 == op2, number=1000000)*1000, 'ns')"
   ```
5. **Track Improvement & Save Commit Association**:
   - Target Metric: `GateOperation.__eq__` latency drops from **942 ns** to **< 100 ns** (9.4x speedup).
   - Record exact commit and metrics in `benchmarks/tracking/task_1_2_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "perf(value): slot-cached method memoization and inlined fast-path value equality"
   git checkout main && git pull origin main && git merge --ff-only perf-fast-equality && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 1.3: Bitmask Moment Collision Engine `[WAVE 2 - TRACK B2: PARALLEL]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P0`
- **Estimated Effort**: 2 days
- **Concurrency**: **Can run concurrently with Task 1.2 and Task 1.5**
- **Dependencies**: Task 1.1
- **Target Files**:
  - `cirq-core/cirq/circuits/moment.py` (`Moment`, `Moment._qubits_and_operations`)
  - `cirq-core/cirq/circuits/circuit.py` (`_PlacementCache`)

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-bitmask-moment origin/main
   ```
2. **Do Changes (Implementation)**:
   - Add an internal qubit-to-bit index registry within `Circuit` or `MomentContext`.
   - Represent moment qubit occupancy as an integer bitmask (`_qubit_bitmask: int`).
   - Replace the `q in self._qubit_to_op` dictionary loop in `Moment.operates_on` and `Moment.can_add` with bitwise operations:
     ```python
     def operates_on(self, qubits: Iterable[Qid]) -> bool:
         op_mask = self._get_qubits_bitmask(qubits)
         return (self._qubit_bitmask & op_mask) != 0
     ```
   - Lazily materialize `_qubit_to_op` dictionary only when indexed by qubit (`moment[qubit]`), saving ~36 KB per 1,000-qubit moment.
3. **Run Tests, Linting & Format Checks**:
   ```bash
   pytest cirq-core/cirq/circuits/moment_test.py cirq-core/cirq/circuits/circuit_test.py -v
   ./check/pytest-changed-files origin/main
   ./check/format-incremental origin/main --apply
   ./check/pylint-changed-files origin/main
   ./check/typecheck
   ./check/misc
   ```
4. **Run Related Benchmarks**:
   ```bash
   python -c "import cirq, timeit; qs=[cirq.LineQubit(i) for i in range(100)]; ops=[cirq.X(q) for q in qs]; print('Moment init 100 ops:', timeit.timeit(lambda: cirq.Moment(ops), number=10000)/10000*1e6, 'us')"
   ```
5. **Track Improvement & Save Commit Association**:
   - Target Metric: Moment instantiation latency on 1000 qubits drops from **6.88 µs** to **< 500 ns** (>13x speedup).
   - Moment collision check drops from **217 ns** to **< 5 ns** (43x speedup).
   - Record exact commit and metrics in `benchmarks/tracking/task_1_3_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "perf(circuits): bitmask-based moment collision detection and lazy dict materialization"
   git checkout main && git pull origin main && git merge --ff-only perf-bitmask-moment && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 1.5: Linear-Time $O(N)$ `CircuitDag` Construction `[WAVE 2 - TRACK C2: PARALLEL]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P0`
- **Estimated Effort**: 1-2 days
- **Concurrency**: **Can run concurrently with Task 1.2 and Task 1.3 (Touches only circuit_dag.py)**
- **Dependencies**: Task 1.1
- **Target Files**:
  - `cirq-core/cirq/circuits/circuit_dag.py` (`CircuitDag.from_circuit`)

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-linear-circuit-dag origin/main
   ```
2. **Do Changes (Implementation)**:
   - Replace pairwise node comparison nested loops with a track-based dependency builder.
   - Maintain `last_node_on_qubit: dict[Qid, Unique[CircuitDagNode]]` and `last_node_on_mkey: dict[MeasurementKey, Unique[CircuitDagNode]]`.
   - For each operation, add directed edges exclusively from `last_node_on_qubit[q]` for each $q \in \text{op.qubits}$, and then update `last_node_on_qubit[q] = new_node`.
   - Eliminate `nx.transitive_reduction` pass by ensuring direct frontier graph construction is already transitive-minimal.
3. **Run Tests, Linting & Format Checks**:
   ```bash
   pytest cirq-core/cirq/circuits/circuit_dag_test.py -v
   ./check/pytest-changed-files origin/main
   ./check/format-incremental origin/main --apply
   ./check/pylint-changed-files origin/main
   ./check/typecheck
   ./check/misc
   ```
4. **Run Related Benchmarks**:
   ```bash
   python -c "import cirq, time; c=cirq.testing.random_circuit(qubits=100, n_moments=500, op_density=0.8); t0=time.perf_counter(); dag=cirq.CircuitDag.from_circuit(c); print('DAG 100x500:', time.perf_counter()-t0, 's')"
   ```
5. **Track Improvement & Save Commit Association**:
   - Target Metric: DAG construction on 100,000 operations runs in **< 0.45s** (was > 10 minutes, >30,000x speedup).
   - Record exact commit and metrics in `benchmarks/tracking/task_1_5_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "perf(circuits): linear-time track-based CircuitDag dependency graph builder"
   git checkout main && git pull origin main && git merge --ff-only perf-linear-circuit-dag && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 1.4: Fast Layer Append & Placement Cache Hardening `[WAVE 3 - TRACK A3: PARALLEL]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P0`
- **Estimated Effort**: 1 day
- **Concurrency**: **Can run concurrently with Task 1.6 and Task 1.8**
- **Dependencies**: Task 1.3
- **Target Files**:
  - `cirq-core/cirq/circuits/circuit.py` (`Circuit.append`, `_PlacementCache`)
  - `cirq-core/cirq/protocols/measurement_key_protocol.py`

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-fast-append origin/main
   ```
2. **Do Changes (Implementation)**:
   - Detect when `Circuit.append(layer)` is passed a pre-validated `Moment` or disjoint operation list.
   - When appending at the end (`strategy=InsertStrategy.NEW`), bypass the backward linear scan in `get_earliest_accommodating_moment_index` and directly append the moment in $O(1)$.
   - Add `_has_measurement_keys = False` fast-path on built-in unitary gates to bypass 1.5M protocol queries in `measurement_key_protocol.py`.
3. **Run Tests, Linting & Format Checks**:
   ```bash
   pytest cirq-core/cirq/circuits/circuit_test.py cirq-core/cirq/protocols/measurement_key_protocol_test.py -v
   ./check/pytest-changed-files origin/main
   ./check/format-incremental origin/main --apply
   ./check/pylint-changed-files origin/main
   ./check/typecheck
   ./check/misc
   ```
4. **Run Related Benchmarks**:
   ```bash
   python -c "import cirq, time; qs=[cirq.GridQubit(i,j) for i in range(50) for j in range(40)]; ops=[cirq.X(q) for q in qs]; c=cirq.Circuit(); t0=time.perf_counter(); [c.append(ops) for _ in range(1000)]; print('Append layerwise 2000x1000:', time.perf_counter()-t0, 's')"
   ```
5. **Track Improvement & Save Commit Association**:
   - Target Metric: Layerwise append time on $2000\times 1000$ (1.5M ops) drops from **31.0 seconds** to **< 2.5 seconds** (>12x speedup).
   - Record exact commit and metrics in `benchmarks/tracking/task_1_4_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "perf(circuits): O(1) fast-path layer append and placement cache optimization"
   git checkout main && git pull origin main && git merge --ff-only perf-fast-append && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 1.6: Topology-Invariant Fast-Path Parameter Resolution `[WAVE 3 - TRACK B3: PARALLEL]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P0`
- **Estimated Effort**: 1 day
- **Concurrency**: **Can run concurrently with Task 1.4 and Task 1.8**
- **Dependencies**: Task 1.3
- **Target Files**:
  - `cirq-core/cirq/protocols/resolve_parameters.py` (`resolve_parameters`)
  - `cirq-core/cirq/circuits/moment.py` (`Moment._resolve_parameters_`)
  - `cirq-core/cirq/circuits/circuit.py` (`Circuit._resolve_parameters_`)

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-fast-param-resolve origin/main
   ```
2. **Do Changes (Implementation)**:
   - Implement `Moment._fast_replace_resolved_ops(new_ops)` that sets `_operations` directly and reuses the existing `_qubit_to_op` dictionary and bitmasks without re-verifying qubit uniqueness.
   - Pre-compile a `ParameterIndexTable = [(moment_idx, op_idx, gate, param_name)]` on parameterized circuits to resolve sweeps directly without traversing unparameterized moments.
3. **Run Tests, Linting & Format Checks**:
   ```bash
   pytest cirq-core/cirq/protocols/resolve_parameters_test.py -v
   ./check/pytest-changed-files origin/main
   ./check/format-incremental origin/main --apply
   ./check/pylint-changed-files origin/main
   ./check/typecheck
   ./check/misc
   ```
4. **Run Related Benchmarks**:
   ```bash
   python -c "import cirq, sympy, time; a=sympy.Symbol('a'); qs=[cirq.LineQubit(i) for i in range(1000)]; c=cirq.Circuit(cirq.X(q)**a for q in qs); t0=time.perf_counter(); [cirq.resolve_parameters(c, {'a': val}) for val in range(100)]; print('Param sweep 1000q x 100 steps:', time.perf_counter()-t0, 's')"
   ```
5. **Track Improvement & Save Commit Association**:
   - Target Metric: Parameter sweep throughput on $1000\times 100$ drops from **546.8 ms** to **< 40 ms** (14x speedup).
   - Record exact commit and metrics in `benchmarks/tracking/task_1_6_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "perf(protocols): topology-invariant parameter resolution and fast moment replacement"
   git checkout main && git pull origin main && git merge --ff-only perf-fast-param-resolve && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 1.8: Batch Operation Insertion in `align_left` and `align_right` `[WAVE 3 - TRACK C3: PARALLEL]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P0`
- **Estimated Effort**: 1 day
- **Concurrency**: **Can run concurrently with Task 1.4 and Task 1.6**
- **Dependencies**: Task 1.3
- **Target Files**:
  - `cirq-core/cirq/transformers/align_left.py` (`align_left`)
  - `cirq-core/cirq/transformers/align_right.py` (`align_right`)

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-batch-align origin/main
   ```
2. **Do Changes (Implementation)**:
   - Replace iterative `ret[i] = ret[i].with_operation(op)` with a track-based placement map `moments_ops: list[list[Operation]] = [[] for _ in range(max_depth)]`.
   - After placing all operations into the grouped lists, construct moments in batch using `cirq.Moment(moments_ops[i])`.
3. **Run Tests, Linting & Format Checks**:
   ```bash
   pytest cirq-core/cirq/transformers/align_left_test.py cirq-core/cirq/transformers/align_right_test.py -v
   ./check/pytest-changed-files origin/main
   ./check/format-incremental origin/main --apply
   ./check/pylint-changed-files origin/main
   ./check/typecheck
   ./check/misc
   ```
4. **Run Related Benchmarks**:
   ```bash
   python -c "import cirq, time; c=cirq.testing.random_circuit(qubits=500, n_moments=200, op_density=0.7); t0=time.perf_counter(); cirq.align_left(c); print('Align left 500x200:', time.perf_counter()-t0, 's')"
   ```
5. **Track Improvement & Save Commit Association**:
   - Target Metric: `align_left` execution time on 1,000 qubits drops from **6.04s** to **< 0.35s (17x speedup)**.
   - Record exact commit and metrics in `benchmarks/tracking/task_1_8_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "perf(transformers): batch moment construction in align_left and align_right"
   git checkout main && git pull origin main && git merge --ff-only perf-batch-align && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 1.10: Vectorized Surface Code & QEC Generator `[WAVE 4 - TRACK D: SYNTHESIS]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P1`
- **Estimated Effort**: 1-2 days
- **Concurrency**: Final Phase 1 Synthesis Task
- **Dependencies**: Task 1.4
- **Target Files**:
  - `cirq-core/cirq/experiments/`
  - `benchmarks/circuit_construction_perf.py`
  - `cirq-core/cirq/circuits/circuit_operation.py`

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-vectorized-qec origin/main
   ```
2. **Do Changes (Implementation)**:
   - Implement `generate_rotated_surface_code_circuit(distance, num_rounds)` using NumPy 2D array coordinate lookups for data and syndrome measure qubits.
   - Implement lazy repetition indexing in `CircuitOperation` (`use_repetition_ids=False` by default) so $T=100,000$ rounds takes $O(1)$ memory.
3. **Run Tests, Linting & Format Checks**:
   ```bash
   pytest benchmarks/circuit_construction_perf.py -v
   ./check/pytest-changed-files origin/main
   ./check/format-incremental origin/main --apply
   ./check/pylint-changed-files origin/main
   ./check/typecheck
   ./check/misc
   ```
4. **Run Related Benchmarks**:
   ```bash
   python benchmarks/circuit_construction_perf.py --test-surface-code --distance 31
   ```
5. **Track Improvement & Save Commit Association**:
   - Target Metric: $d=31, T=31$ surface code construction drops from **40.82 ms (MbM) / 801.97 ms (ObO)** to **< 5 ms**.
   - $d=31, T=10,000$ rounds takes **< 10 MB** of memory (was OOM).
   - Record exact commit and metrics in `benchmarks/tracking/task_1_10_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "perf(qec): vectorized rotated surface code generator and lazy repetition subcircuits"
   git checkout main && git pull origin main && git merge --ff-only perf-vectorized-qec && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.
   Phase 1 Complete. Proceed to **Phase 2**.

---

## 3. Phase 2: Native Rust Hybrid Core (`cirq_core_rs` via PyO3)

### Task 2.1: Rust Workspace & Maturin Build Scaffolding `[PHASE 2 - WAVE 1]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P1`
- **Estimated Effort**: 2-3 days
- **Dependencies**: Phase 1 Complete
- **Target Files**:
  - `Cargo.toml` (workspace root)
  - `crates/cirq-core-rs/Cargo.toml`, `src/lib.rs`
  - `pyproject.toml` (integrate `maturin` PEP 517 build backend)
  - `.github/workflows/wheels.yml` (configure `cibuildwheel` for manylinux, musllinux, macos, windows)

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-rust-scaffolding origin/main
   ```
2. **Do Changes (Implementation)**:
   - Setup Rust workspace with `pyo3 = { version = "0.22", features = ["extension-module", "abi3-py310"] }`.
   - Setup fallback mechanism: `try: from cirq._core_rs import ... except ImportError: ...`.
3. **Run Tests, Linting & Format Checks**:
   ```bash
   cargo test --manifest-path crates/cirq-core-rs/Cargo.toml
   cargo clippy --manifest-path crates/cirq-core-rs/Cargo.toml --all-targets -- -D warnings
   cargo fmt --manifest-path crates/cirq-core-rs/Cargo.toml --check
   maturin develop -m crates/cirq-core-rs/Cargo.toml
   pytest cirq-core/ -v
   ./check/pytest-changed-files origin/main
   ./check/format-incremental origin/main --apply
   ./check/pylint-changed-files origin/main
   ./check/typecheck
   ./check/misc
   ```
4. **Run Related Benchmarks**: Verify zero regression on existing pure-Python suite with native module loaded.
5. **Track Improvement & Save Commit Association**: Record exact commit and metrics in `benchmarks/tracking/task_2_1_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "feat(native): scaffold cirq-core-rs rust workspace with pyo3 abi3 bindings"
   git checkout main && git pull origin main && git merge --ff-only perf-rust-scaffolding && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 2.2: Qubit Registry & Interned Integer ID System `[PHASE 2 - WAVE 1]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P1`
- **Estimated Effort**: 2 days
- **Dependencies**: Task 2.1
- **Target Files**:
  - `crates/cirq-core-rs/src/qubit_registry.rs`

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-rust-qubit-registry origin/main
   ```
2. **Do Changes (Implementation)**:
   - Implement `QubitRegistry` maintaining bi-directional mapping between Python `Qid` instances and dense `u32` integer indices.
   - Provide lock-free read access for standard line and grid qubit lookups.
3. **Run Tests, Linting & Format Checks**:
   ```bash
   cargo test --manifest-path crates/cirq-core-rs/Cargo.toml qubit_registry
   cargo clippy --manifest-path crates/cirq-core-rs/Cargo.toml --all-targets -- -D warnings
   cargo fmt --manifest-path crates/cirq-core-rs/Cargo.toml --check
   ```
4. **Run Related Benchmarks**: Benchmark 1,000,000 qubit interning lookups: verify < 15 ns per lookup.
5. **Track Improvement & Save Commit Association**: Record exact commit and metrics in `benchmarks/tracking/task_2_2_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "feat(native): lock-free QubitRegistry interning system for cirq-core-rs"
   git checkout main && git pull origin main && git merge --ff-only perf-rust-qubit-registry && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 2.3: `PackedOp` Contiguous Memory Arena & `StandardGate` Enum `[PHASE 2 - WAVE 2: PARALLEL]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P1`
- **Estimated Effort**: 3 days
- **Concurrency**: **Can run concurrently with Task 2.4**
- **Dependencies**: Task 2.2
- **Target Files**:
  - `crates/cirq-core-rs/src/op.rs`, `src/gates.rs`

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-rust-packed-op origin/main
   ```
2. **Do Changes (Implementation)**:
   - Define 16-byte contiguous `PackedOp` struct:
     ```rust
     #[repr(C)]
     pub struct PackedOp {
         pub gate_id: u16,
         pub flags: u16,
         pub qubit_0: u32,
         pub qubit_1: u32,
         pub param_index: u32,
     }
     ```
   - Define `StandardGate` enum covering Pauli, Clifford, Rotation, FSim, Sycamore, and Measurement gates.
   - Provide `Custom(Py<PyAny>)` variant for arbitrary user-defined duck-typed Python gates.
3. **Run Tests, Linting & Format Checks**:
   ```bash
   cargo test --manifest-path crates/cirq-core-rs/Cargo.toml op
   cargo clippy --manifest-path crates/cirq-core-rs/Cargo.toml --all-targets -- -D warnings
   cargo fmt --manifest-path crates/cirq-core-rs/Cargo.toml --check
   ```
4. **Run Related Benchmarks**: Allocate 1,000,000 `PackedOp` instances in Rust arena: verify memory footprint is exactly **16.0 MB** (was 2.45 GB).
5. **Track Improvement & Save Commit Association**: Record exact commit and metrics in `benchmarks/tracking/task_2_3_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "feat(native): 16-byte PackedOp contiguous memory arena and StandardGate enum"
   git checkout main && git pull origin main && git merge --ff-only perf-rust-packed-op && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 2.4: SIMD BitVec Moment Collision Engine `[PHASE 2 - WAVE 2: PARALLEL]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P1`
- **Estimated Effort**: 2 days
- **Concurrency**: **Can run concurrently with Task 2.3**
- **Dependencies**: Task 2.2
- **Target Files**:
  - `crates/cirq-core-rs/src/moment.rs`

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-rust-simd-moment origin/main
   ```
2. **Do Changes (Implementation)**:
   - Represent moment occupancy using AVX2 / AVX-512 256-bit / 512-bit vector bitsets (`bitvec` crate).
   - Implement collision check via SIMD `_mm256_testz_si256` or equivalent intrinsics (< 1 ns collision test).
3. **Run Tests, Linting & Format Checks**:
   ```bash
   cargo test --manifest-path crates/cirq-core-rs/Cargo.toml moment
   cargo clippy --manifest-path crates/cirq-core-rs/Cargo.toml --all-targets -- -D warnings
   cargo fmt --manifest-path crates/cirq-core-rs/Cargo.toml --check
   ```
4. **Run Related Benchmarks**: Benchmark collision check across 10,000 moments: verify throughput > 500,000,000 checks/sec.
5. **Track Improvement & Save Commit Association**: Record exact commit and metrics in `benchmarks/tracking/task_2_4_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "feat(native): AVX2/AVX-512 SIMD bitvector moment collision engine"
   git checkout main && git pull origin main && git merge --ff-only perf-rust-simd-moment && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 2.5: Native `CircuitData` & Lazy `MomentView` Python Bindings `[PHASE 2 - WAVE 3]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P1`
- **Estimated Effort**: 3-4 days
- **Dependencies**: Task 2.3, Task 2.4
- **Target Files**:
  - `crates/cirq-core-rs/src/circuit.rs`, `src/python_bindings.rs`

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-rust-circuit-data origin/main
   ```
2. **Do Changes (Implementation)**:
   - Implement `CircuitData` managing a `Vec<PackedOp>` arena and moment index boundary tables.
   - Expose `MomentView` and `OperationView` to Python for zero-copy indexing (`circuit[i]`).
3. **Run Tests, Linting & Format Checks**:
   ```bash
   cargo test --manifest-path crates/cirq-core-rs/Cargo.toml
   cargo clippy --manifest-path crates/cirq-core-rs/Cargo.toml --all-targets -- -D warnings
   cargo fmt --manifest-path crates/cirq-core-rs/Cargo.toml --check
   maturin develop -m crates/cirq-core-rs/Cargo.toml
   pytest cirq-core/cirq/circuits/ -v
   ./check/pytest-changed-files origin/main
   ./check/format-incremental origin/main --apply
   ./check/typecheck
   ```
4. **Run Related Benchmarks**: Benchmark $1000 \times 1000$ circuit construction in Python wrapping native `CircuitData`.
5. **Track Improvement & Save Commit Association**: Target Metric: Construction time on 1.5M ops drops from **1.17s** to **0.18s (82x speedup)**. Record in `benchmarks/tracking/task_2_5_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "feat(native): CircuitData arena and zero-copy MomentView PyO3 bindings"
   git checkout main && git pull origin main && git merge --ff-only perf-rust-circuit-data && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 2.6: Native Transpilation Passes & SABRE Routing `[PHASE 2 - WAVE 4: PARALLEL]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P2`
- **Estimated Effort**: 3-5 days
- **Concurrency**: **Can run concurrently with Task 2.7**
- **Dependencies**: Task 2.5
- **Target Files**:
  - `crates/cirq-core-rs/src/transformers/`

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-rust-transformers origin/main
   ```
2. **Do Changes (Implementation)**:
   - Implement native parallel `merge_single_qubit_moments`, `drop_empty_moments`, and `eject_paulis` running across Rayon threads with zero Python GIL contention.
   - Implement native SABRE swap routing on hardware topology graphs using `petgraph`.
3. **Run Tests, Linting & Format Checks**:
   ```bash
   cargo test --manifest-path crates/cirq-core-rs/Cargo.toml transformers
   cargo clippy --manifest-path crates/cirq-core-rs/Cargo.toml --all-targets -- -D warnings
   cargo fmt --manifest-path crates/cirq-core-rs/Cargo.toml --check
   maturin develop -m crates/cirq-core-rs/Cargo.toml
   pytest cirq-core/cirq/transformers/ -v
   ./check/pytest-changed-files origin/main
   ./check/format-incremental origin/main --apply
   ./check/typecheck
   ```
4. **Run Related Benchmarks**: Benchmark transformer pipeline on 1M operations: verify single-qubit moment merger runs in **< 0.05s** (was 3.97s, 79x speedup).
5. **Track Improvement & Save Commit Association**: Record exact commit and metrics in `benchmarks/tracking/task_2_6_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "feat(native): multi-threaded compiler passes and SABRE routing in Rust"
   git checkout main && git pull origin main && git merge --ff-only perf-rust-transformers && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.

---

### Task 2.7: Native `RepeatBlock` AST & Stim / OpenQASM 3.0 Bridge `[PHASE 2 - WAVE 4: PARALLEL]`
- **Status**: `[ ] Pending` <!-- Agent: Update to `[x] Completed (Commit: <sha>)` when finished -->
- **Priority**: `P2`
- **Estimated Effort**: 2-3 days
- **Concurrency**: **Can run concurrently with Task 2.6**
- **Dependencies**: Task 2.5
- **Target Files**:
  - `crates/cirq-core-rs/src/repeat_block.rs`, `src/export.rs`

#### Execution Workflow:
1. **Create Feature Branch**:
   ```bash
   git fetch origin
   git checkout -b perf-rust-repeat-block origin/main
   ```
2. **Do Changes (Implementation)**:
   - Implement first-class `RepeatBlock` AST node representing $T$ repeated moments in $O(1)$ memory.
   - Implement zero-copy export to Stim `stim::Circuit` and OpenQASM 3.0.
3. **Run Tests, Linting & Format Checks**:
   ```bash
   cargo test --manifest-path crates/cirq-core-rs/Cargo.toml repeat_block
   cargo clippy --manifest-path crates/cirq-core-rs/Cargo.toml --all-targets -- -D warnings
   cargo fmt --manifest-path crates/cirq-core-rs/Cargo.toml --check
   maturin develop -m crates/cirq-core-rs/Cargo.toml
   pytest cirq-core/cirq/interop/ -v
   ./check/pytest-changed-files origin/main
   ./check/format-incremental origin/main --apply
   ./check/typecheck
   ```
4. **Run Related Benchmarks**: Export 100,000-round surface code circuit to Stim format: verify < 50 ms export latency (188x speedup).
5. **Track Improvement & Save Commit Association**: Record exact commit and metrics in `benchmarks/tracking/task_2_7_$(git rev-parse HEAD).json`.
6. **Commit & Merge to Fork**:
   ```bash
   git commit -S -m "feat(native): native RepeatBlock AST and zero-copy Stim/QASM bridge"
   git checkout main && git pull origin main && git merge --ff-only perf-rust-repeat-block && git push origin main
   ```
7. **Mark Finished**: Update status above to `[x] Completed (Commit: <commit_sha>)`.
   Phase 2 Complete.

---

## 4. Recommended Preparation Steps

Before beginning task implementation, the following foundational preparation steps MUST be executed:

### 4.1 Benchmark Baseline Suite Freeze & JSON Serialization
- **Objective**: Establish an immutable performance baseline against which all Phase 1 and Phase 2 PRs are measured.
- **Action**:
  1. Run the comprehensive benchmark suite across all scale matrix configurations ($N \in [10..2000]$, $D \in [10..1000]$, $d \in [3..31]$).
  2. Serialize the complete results into `benchmarks/baseline_results.json`.
  3. Check in `benchmarks/baseline_results.json` to git version control on `origin/main`.

### 4.2 Automated Property-Based Invariant Testing Harness
- **Objective**: Ensure that aggressive performance refactorings (such as `__slots__`, bitmask collisions, and fast-path parameter resolution) introduce **zero semantic regressions** or subtle behavioral bugs.
- **Action**:
  1. Create a property-based test harness using `hypothesis` in `cirq-core/cirq/testing/property_tests.py`.
  2. Test invariants on 10,000 randomly generated circuits:
     - Circuit equality: `circuit_optimized == circuit_reference`
     - Decomposition invariance: `cirq.unitary(c) == cirq.unitary(cirq.decompose(c))`
     - Parameter substitution invariance: `cirq.resolve_parameters(c, params) == legacy_resolve(c, params)`
     - Diagram info & JSON serialization round-tripping.

### 4.3 Pre-commit Hook & Incremental Formatting Setup
- **Objective**: Ensure all modified code adheres strictly to Cirq formatting and linting rules before commits are created.
- **Action**:
  1. Configure pre-commit hook to invoke incremental formatting:
     ```bash
     ./check/format-incremental --apply
     ```
  2. Verify that SSH commit signing is active (`git config user.signingkey ~/.ssh/id_ed25519`).

### 4.4 Subagent Execution Strategy & Workload Allocation
- **Objective**: Orchestrate concurrent pair-programming workflows across specialized subagents without merge conflicts.
- **Action**:
  1. Isolate work into independent feature branches per task (e.g. Wave 1 branches `perf-universal-slots`, `perf-scipy-routing-init`, `perf-fast-decompose`).
  2. Execute Wave 1 subagents concurrently across disjoint directories.
  3. Rebase feature branches on `origin/main` before fast-forward merging into `origin/main`.

### 4.5 Performance CI & Regression Guard Configuration
- **Objective**: Automatically block any pull request or commit that introduces a performance regression > 5%.
- **Action**:
  1. Add a GitHub Actions / CI workflow step running `pytest-benchmark`.
  2. Compare benchmark run against `benchmarks/baseline_results.json`.
  3. Fail presubmit checks if mean latency increases by > 5% on any scale configuration.
