# Cirq Open Source Development Guidelines

This workspace is a Git checkout of the open-source [quantumlib/Cirq](https://github.com/quantumlib/Cirq) project.

## 🐍 Python Environment & Dependencies
- **Virtual Environment**: Active Python 3.13 virtual environment (`.venv` / `cirq-dev`)
- **Installed Packages**: `cirq-core`, `cirq-google`, `cirq-aqt`, `cirq-ionq`, `cirq-pasqal`, `cirq-web` (all in editable mode `-e`), plus pytest, ruff, black, and development dependencies.

## 🧪 Testing, Linting & Verification Commands
Always run the complete verification suite before committing:
- **Run targeted module tests**:
  ```bash
  pytest <test_paths> -v
  ```
- **Run tests on changed files**:
  ```bash
  ./check/pytest-changed-files origin/main
  ```
- **Apply incremental code formatting (Ruff, Black, isort)**:
  ```bash
  ./check/format-incremental origin/main --apply
  ```
- **Run linter on changed files (Pylint)**:
  ```bash
  ./check/pylint-changed-files origin/main
  ```
- **Run static type checking (Mypy)**:
  ```bash
  ./check/typecheck
  ```
- **Run codebase hygiene & formatting checks**:
  ```bash
  ./check/misc
  ```
- **Run Cirq fast pytest harness**:
  ```bash
  ./check/pytest
  ```
- **Run Native Rust checks (Phase 2 modules)**:
  ```bash
  cargo test --workspace
  cargo clippy --workspace --all-targets -- -D warnings
  cargo fmt --check
  ```

## 🛡️ Pre-Merge GitHub Actions CI Equivalence Gate (.github/workflows/ci.yml)
To ensure 100% pass rate on GitHub Actions CI when merging to the Fork (`origin/main`), all changes MUST pass the local equivalent checks defined in [.github/workflows/ci.yml](file:///usr/local/google/home/andriyku/workspace/Cirq/.github/workflows/ci.yml):

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

## 🐙 Git & GitHub Workflow
- **Upstream Repository (Read-Only / Fetch Only)**: `git@github.com:quantumlib/Cirq.git` (tracking branch: `upstream/main`)
- **Fork Remote (Target for all Merges & Pushes)**: `git@github.com:akushnarov/Cirq.git` (tracking branch: `origin/main`)
- **CRITICAL MERGE RULE**: **NEVER merge or push directly to `upstream/main`! All development, feature branches, commits, and PR merges MUST ONLY target the Fork (`origin/main` / `origin`).**
- **Syncing fork with upstream**:
  ```bash
  git fetch upstream
  git rebase upstream/main
  git push origin origin/main
  ```
- **Branching for a task**:
  ```bash
  git checkout -b perf-task-name origin/main
  ```
- **Standardized Task Execution Routine (Strict 7-Step Lifecycle)**:
  1. **Create Feature Branch**: `git checkout -b <branch_name> origin/main`
  2. **Do Changes (Implementation)**: Edit target files, classes, and methods.
  3. **Run Tests, Linting & CI Quality Checks**:
     - Fast CI Pipeline: `./check/all --changed origin/main`
     - Targeted Unit Tests: `pytest <test_paths> -v`
     - Incremental Formatting: `./check/format-incremental origin/main --apply`
     - Linting: `ruff check` && `./check/pylint-changed-files origin/main`
     - Static Type Checking: `FORCE_COLOR=1 ./check/typecheck`
     - Repo Hygiene: `./check/misc`
     - (For Phase 2 Rust tasks): `cargo test --workspace && cargo clippy --workspace --all-targets -- -D warnings && cargo fmt --check`
  4. **Run Related Benchmarks**: Execute benchmark script and capture metrics.
  5. **Track Improvement & Associate Specific Commit**: Always capture and save the exact branch and commit SHA (`git rev-parse HEAD`, `git branch --show-current`) alongside benchmark measurements in `benchmarks/tracking/` so specific commits can be audited, compared, or cherry-picked.
  6. **Pre-Merge CI Validation & Commit/Merge to Fork**:
     - Verify full CI parity: `./check/all --changed origin/main` exits with code 0.
     - Signed commit: `git commit -S -m "<type>(<scope>): <description>"`
     - Merge ONLY to Fork: `git checkout main && git pull origin main && git merge --ff-only <branch_name> && git push origin main`
  7. **Mark Task as Finished in TASKS.md**: The agent MUST update `TASKS.md` to change the task status to `- **Status**: [x] Completed (Commit: <commit_sha>)` and record final benchmark speedup.
- **Commit signing**: Automatically enabled with SSH signing key (`~/.ssh/id_ed25519`).
- **Commit message convention**: Include issue references or descriptive scope tags, e.g. `perf(core): ...`.

## 📋 Task Completion & Documentation Protocol
Whenever an agent finishes executing and validating a task:
1. **Update `TASKS.md` Status**: Change `- **Status**: [ ] Pending` to `- **Status**: [x] Completed (Commit: <commit_sha>)`.
2. **Record Commit SHA & Benchmark Record**: Ensure the tracking JSON is generated in `benchmarks/tracking/<task_id>_<commit_sha>.json` and metrics are summarized under the task in `TASKS.md`.
3. **Always Commit Documentation (.md) & Tracking Files**: Agents MUST always stage and commit all modified Markdown documents (`AGENTS.md`, `OPTIMISATION_PROPOSITION.md`, `TASKS.md`) and tracking JSON files (`benchmarks/tracking/`) alongside or immediately after task completion so that project status, task tracking, and repository history remain 100% in sync on `origin/main`.
4. **Verify Git Tree & Push**: Ensure the branch and all documentation changes have cleanly merged and pushed into `origin/main` before moving to dependent tasks.

## 🧬 Cirq Code Architecture & Best Practices
1. **Subpackages**:
   - `cirq-core`: Base classes, qubits, gates, circuits, simulators, protocols, Pauli algebra.
   - `cirq-google`: Google quantum hardware targets (Sycamore, Willow), Quantum Engine API, calibration data, serialization.
   - `cirq-aqt`, `cirq-ionq`, `cirq-pasqal`, `cirq-web`: Third-party vendor devices and web visualizers.
2. **Protocols**: Always implement relevant Cirq protocols for new gates and operations (`cirq.SupportsUnitary`, `cirq.SupportsDecompose`, `cirq.SupportsParameterization`, `cirq.SupportsCircuitDiagramInfo`).
3. **Immutability**: Cirq gate and operation objects should be immutable whenever possible (using `@cirq.value.value_equality` or dataclass immutability).
4. **Serialization**: Any new gate or feature intended for engine execution must support JSON serialization in `cirq/protocols/json_serialization.py` or `cirq_google`.
5. **Subagent Parallelization**: Independent tasks that touch disjoint modules (e.g. `cirq/protocols/` vs `cirq/transformers/routing/` vs `cirq/ops/`) should be executed concurrently in separate subagents on isolated feature branches.
