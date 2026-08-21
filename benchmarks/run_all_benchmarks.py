# Copyright 2026 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Comprehensive benchmark runner comparing Before vs After performance metrics."""

import gc
import json
import time
import tracemalloc
import networkx as nx
import numpy as np
import sympy

import cirq
from cirq.experiments.surface_code import (
    SurfaceCodePatch,
    rotated_surface_code_cycle,
    generate_rotated_surface_code_circuit,
)
from benchmarks.circuit_construction_perf import (
    surface_code_circuit as benchmark_surface_code_circuit,
)


def measure_time(func, number=1, repeat=3):
    best = float('inf')
    for _ in range(repeat):
        gc.disable()
        t0 = time.perf_counter()
        for _ in range(number):
            func()
        t1 = time.perf_counter()
        gc.enable()
        elapsed = (t1 - t0) / number
        if elapsed < best:
            best = elapsed
    return best


def run_benchmarks():
    results = []

    def record(category, name, before_val, before_unit, after_val, after_unit, lower_is_better=True):
        if before_unit == after_unit:
            abs_shift = after_val - before_val
            pct_shift = ((after_val - before_val) / before_val) * 100 if before_val != 0 else 0
            if lower_is_better:
                speedup = before_val / after_val if after_val != 0 else float('inf')
            else:
                speedup = after_val / before_val if before_val != 0 else float('inf')
        else:
            abs_shift = None
            pct_shift = None
            speedup = None

        entry = {
            "category": category,
            "name": name,
            "before_str": f"{before_val:,.2f} {before_unit}" if isinstance(before_val, float) else f"{before_val} {before_unit}",
            "after_str": f"{after_val:,.2f} {after_unit}" if isinstance(after_val, float) else f"{after_val} {after_unit}",
            "before_val": before_val,
            "after_val": after_val,
            "unit": after_unit,
            "abs_shift": abs_shift,
            "pct_shift": pct_shift,
            "speedup": speedup,
        }
        results.append(entry)
        shift_str = f"Shift={pct_shift:+.2f}%" if pct_shift is not None else ""
        sp_str = f"({speedup:.2f}x speedup)" if speedup and speedup >= 1.0 else (f"({1/speedup:.2f}x slowdown)" if speedup else "")
        print(f"[{category}] {name}: Before={entry['before_str']} | After={entry['after_str']} | {shift_str} {sp_str}")

    print("=== 1. Object Instantiation Latency & Equality ===")

    # LineQubit
    t_lq = measure_time(lambda: [cirq.LineQubit(i) for i in range(1000)], number=20) / 1000 * 1e9
    record("1. Object Instantiation", "cirq.LineQubit(i) instantiation latency", 1435.8, "ns", round(t_lq, 2), "ns")

    # GridQubit
    t_gq = measure_time(lambda: [cirq.GridQubit(r, c) for r in range(30) for c in range(30)], number=20) / 900 * 1e9
    record("1. Object Instantiation", "cirq.GridQubit(r, c) instantiation latency", 1636.1, "ns", round(t_gq, 2), "ns")

    # GateOperation cirq.X(q)
    q0 = cirq.LineQubit(0)
    t_x = measure_time(lambda: [cirq.X(q0) for _ in range(1000)], number=20) / 1000 * 1e9
    record("1. Object Instantiation", "cirq.X(q) gate operation latency", 2910.7, "ns", round(t_x, 2), "ns")

    # CNOT(q0, q1)
    q1 = cirq.LineQubit(1)
    t_cx = measure_time(lambda: [cirq.CNOT(q0, q1) for _ in range(1000)], number=20) / 1000 * 1e9
    record("1. Object Instantiation", "cirq.CNOT(q0, q1) gate operation latency", 1736.9, "ns", round(t_cx, 2), "ns")

    # Moment(100_ops)
    qs100 = [cirq.LineQubit(i) for i in range(100)]
    ops100 = [cirq.X(q) for q in qs100]
    t_m100 = measure_time(lambda: cirq.Moment(ops100), number=2000) * 1e6
    record("1. Object Instantiation", "cirq.Moment(100 ops) init latency", 50.0, "µs", round(t_m100, 2), "µs")

    # Moment(1000_ops)
    qs1000 = [cirq.LineQubit(i) for i in range(1000)]
    ops1000 = [cirq.X(q) for q in qs1000]
    t_m1000 = measure_time(lambda: cirq.Moment(ops1000), number=500) * 1e6
    record("1. Object Instantiation", "cirq.Moment(1,000 ops) init latency", 688.0, "µs", round(t_m1000, 2), "µs")

    # GateOperation __eq__
    op1 = cirq.X(q0)
    op2 = cirq.X(q0)
    t_eq = measure_time(lambda: op1 == op2, number=100000) * 1e9
    record("1. Object Instantiation", "GateOperation.__eq__ (op1 == op2) latency", 942.0, "ns", round(t_eq, 2), "ns")

    # Symmetric CZ equality
    cz1 = cirq.CZ(q0, q1)
    cz2 = cirq.CZ(q1, q0)
    t_cz_eq = measure_time(lambda: cz1 == cz2, number=50000) * 1e9
    record("1. Object Instantiation", "Symmetric 2Q Gate Equality (CZ(0,1) == CZ(1,0))", 1976.95, "ns", round(t_cz_eq, 2), "ns")


    print("\n=== 2. Circuit Construction Latency & Throughput ===")

    # 100x100 layerwise append (7500 ops)
    qs_100x100 = [cirq.GridQubit(i, j) for i in range(10) for j in range(10)]
    ops_100x100 = [cirq.X(q) for q in qs_100x100]
    def run_append_100x100():
        c = cirq.Circuit()
        for _ in range(100):
            c.append(ops_100x100)
    t_app_100x100 = measure_time(run_append_100x100, number=10) * 1000
    record("2. Circuit Construction", "Circuit.append layerwise (100q x 100 moments)", 41.21, "ms", round(t_app_100x100, 2), "ms")

    # 1000x100 layerwise append (75k ops)
    qs_1000x100 = [cirq.GridQubit(i, j) for i in range(50) for j in range(20)]
    ops_1000x100 = [cirq.X(q) for q in qs_1000x100]
    def run_append_1000x100():
        c = cirq.Circuit()
        for _ in range(100):
            c.append(ops_1000x100)
    t_app_1000x100 = measure_time(run_append_1000x100, number=5) * 1000
    record("2. Circuit Construction", "Circuit.append layerwise (1,000q x 100 moments)", 852.0, "ms", round(t_app_1000x100, 2), "ms")

    # 1000x1000 layerwise append (750k ops)
    def run_append_1000x1000():
        c = cirq.Circuit()
        for _ in range(1000):
            c.append(ops_1000x100)
    t_app_1000x1000 = measure_time(run_append_1000x1000, number=2) * 1000
    record("2. Circuit Construction", "Circuit.append layerwise (1,000q x 1,000 moments)", 8764.7, "ms", round(t_app_1000x1000, 2), "ms")

    # 2000x1000 layerwise append (1.5M ops)
    qs_2000x1000 = [cirq.GridQubit(i, j) for i in range(50) for j in range(40)]
    ops_2000x1000 = [cirq.X(q) for q in qs_2000x1000]
    def run_append_2000x1000():
        c = cirq.Circuit()
        for _ in range(1000):
            c.append(ops_2000x1000)
    t_app_2000x1000 = measure_time(run_append_2000x1000, number=1)
    record("2. Circuit Construction", "Circuit.append layerwise (2,000q x 1,000 moments, 1.5M ops)", 30.99, "s", round(t_app_2000x1000, 3), "s")

    # 2000x1000 direct moment append
    mom_2000 = cirq.Moment(ops_2000x1000)
    def run_mom_append_2000x1000():
        c = cirq.Circuit()
        for _ in range(1000):
            c.append(mom_2000)
    t_mom_app = measure_time(run_mom_append_2000x1000, number=5) * 1000
    record("2. Circuit Construction", "Circuit.append direct Moment (2,000q x 1,000 moments)", 1167.6, "ms", round(t_mom_app, 2), "ms")


    print("\n=== 3. Surface Code Construction Benchmarks (T=d rounds) ===")

    # d=3 (17q, T=3 rounds, 129 ops)
    t_sc_d3_mbm = measure_time(lambda: benchmark_surface_code_circuit(3, 3, moment_by_moment=True), number=10) * 1000
    t_sc_d3_obo = measure_time(lambda: benchmark_surface_code_circuit(3, 3, moment_by_moment=False), number=10) * 1000
    record("3. Surface Code QEC", "Surface Code d=3 (17 qubits, T=3 rounds) MbM", 0.77, "ms", round(t_sc_d3_mbm, 3), "ms")
    record("3. Surface Code QEC", "Surface Code d=3 (17 qubits, T=3 rounds) ObO", 1.45, "ms", round(t_sc_d3_obo, 3), "ms")

    # d=5 (49q, T=5 rounds, 665 ops)
    t_sc_d5_mbm = measure_time(lambda: benchmark_surface_code_circuit(5, 5, moment_by_moment=True), number=10) * 1000
    t_sc_d5_obo = measure_time(lambda: benchmark_surface_code_circuit(5, 5, moment_by_moment=False), number=10) * 1000
    record("3. Surface Code QEC", "Surface Code d=5 (49 qubits, T=5 rounds) MbM", 1.63, "ms", round(t_sc_d5_mbm, 3), "ms")
    record("3. Surface Code QEC", "Surface Code d=5 (49 qubits, T=5 rounds) ObO", 5.45, "ms", round(t_sc_d5_obo, 3), "ms")

    # d=7 (97q, T=7 rounds, 1,897 ops)
    t_sc_d7_mbm = measure_time(lambda: benchmark_surface_code_circuit(7, 7, moment_by_moment=True), number=10) * 1000
    t_sc_d7_obo = measure_time(lambda: benchmark_surface_code_circuit(7, 7, moment_by_moment=False), number=10) * 1000
    record("3. Surface Code QEC", "Surface Code d=7 (97 qubits, T=7 rounds) MbM", 2.61, "ms", round(t_sc_d7_mbm, 3), "ms")
    record("3. Surface Code QEC", "Surface Code d=7 (97 qubits, T=7 rounds) ObO", 8.33, "ms", round(t_sc_d7_obo, 3), "ms")

    # d=9 (161q, T=9 rounds, 4,113 ops)
    t_sc_d9_mbm = measure_time(lambda: benchmark_surface_code_circuit(9, 9, moment_by_moment=True), number=5) * 1000
    t_sc_d9_obo = measure_time(lambda: benchmark_surface_code_circuit(9, 9, moment_by_moment=False), number=5) * 1000
    record("3. Surface Code QEC", "Surface Code d=9 (161 qubits, T=9 rounds) MbM", 3.63, "ms", round(t_sc_d9_mbm, 3), "ms")
    record("3. Surface Code QEC", "Surface Code d=9 (161 qubits, T=9 rounds) ObO", 15.66, "ms", round(t_sc_d9_obo, 3), "ms")

    # d=11 (241q, T=11 rounds, 7,601 ops)
    t_sc_d11_mbm = measure_time(lambda: benchmark_surface_code_circuit(11, 11, moment_by_moment=True), number=5) * 1000
    t_sc_d11_obo = measure_time(lambda: benchmark_surface_code_circuit(11, 11, moment_by_moment=False), number=5) * 1000
    record("3. Surface Code QEC", "Surface Code d=11 (241 qubits, T=11 rounds) MbM", 5.14, "ms", round(t_sc_d11_mbm, 3), "ms")
    record("3. Surface Code QEC", "Surface Code d=11 (241 qubits, T=11 rounds) ObO", 28.81, "ms", round(t_sc_d11_obo, 3), "ms")

    # d=15 (449q, T=15 rounds, 19,545 ops)
    t_sc_d15_mbm = measure_time(lambda: benchmark_surface_code_circuit(15, 15, moment_by_moment=True), number=3) * 1000
    t_sc_d15_obo = measure_time(lambda: benchmark_surface_code_circuit(15, 15, moment_by_moment=False), number=3) * 1000
    record("3. Surface Code QEC", "Surface Code d=15 (449 qubits, T=15 rounds) MbM", 8.94, "ms", round(t_sc_d15_mbm, 3), "ms")
    record("3. Surface Code QEC", "Surface Code d=15 (449 qubits, T=15 rounds) ObO", 71.69, "ms", round(t_sc_d15_obo, 3), "ms")

    # d=21 (881q, T=21 rounds, 54,201 ops)
    t_sc_d21_mbm = measure_time(lambda: benchmark_surface_code_circuit(21, 21, moment_by_moment=True), number=2) * 1000
    t_sc_d21_obo = measure_time(lambda: benchmark_surface_code_circuit(21, 21, moment_by_moment=False), number=2) * 1000
    record("3. Surface Code QEC", "Surface Code d=21 (881 qubits, T=21 rounds) MbM", 16.19, "ms", round(t_sc_d21_mbm, 3), "ms")
    record("3. Surface Code QEC", "Surface Code d=21 (881 qubits, T=21 rounds) ObO", 219.56, "ms", round(t_sc_d21_obo, 3), "ms")

    # d=31 (1921q, T=31 rounds, 175,801 ops)
    t_sc_d31_mbm = measure_time(lambda: benchmark_surface_code_circuit(31, 31, moment_by_moment=True), number=2) * 1000
    t_sc_d31_obo = measure_time(lambda: benchmark_surface_code_circuit(31, 31, moment_by_moment=False), number=1) * 1000
    record("3. Surface Code QEC", "Surface Code d=31 (1,921 qubits, T=31 rounds, 175k ops) MbM", 40.82, "ms", round(t_sc_d31_mbm, 2), "ms")
    record("3. Surface Code QEC", "Surface Code d=31 (1,921 qubits, T=31 rounds, 175k ops) ObO", 801.97, "ms", round(t_sc_d31_obo, 2), "ms")

    # d=31, T=10,000 rounds subcircuit memory
    tracemalloc.start()
    c_10k = generate_rotated_surface_code_circuit(31, num_rounds=10000, as_subcircuit=True)
    _, peak_mem_10k = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mem_10k_mb = peak_mem_10k / (1024 * 1024)
    record("3. Surface Code QEC", "Surface Code d=31, T=10,000 rounds Peak Memory", 2450.0, "MB", round(peak_mem_10k_mb, 2), "MB")


    print("\n=== 4. Protocols, Transformers & DAGs ===")

    # MappingManager (N=1000)
    g = nx.grid_2d_graph(50, 20)
    mapping = {cirq.LineQubit(i): cirq.GridQubit(*node) for i, node in enumerate(g.nodes())}
    dev_graph = nx.relabel_nodes(g, lambda node: cirq.GridQubit(*node))
    t_mm = measure_time(lambda: cirq.transformers.routing.mapping_manager.MappingManager(dev_graph, mapping), number=5)
    record("4. Graph & Routing", "MappingManager(50x20 Grid, N=1,000) Initialization", 106.99, "s", round(t_mm, 4), "s")

    # CircuitDag.from_circuit on 10k ops
    c_dag_10k = cirq.Circuit(cirq.X(cirq.LineQubit(i)) for i in range(1000) for _ in range(10))
    t_dag_10k = measure_time(lambda: cirq.CircuitDag.from_circuit(c_dag_10k), number=5)
    record("4. Graph & Routing", "CircuitDag.from_circuit (10,000 operations)", 25.33, "s", round(t_dag_10k, 4), "s")

    # CircuitDag.from_circuit on random 100x500 (28k ops)
    c_dag_rand = cirq.testing.random_circuit(qubits=100, n_moments=500, op_density=0.8, random_state=42)
    t_dag_rand = measure_time(lambda: cirq.CircuitDag.from_circuit(c_dag_rand), number=3)
    record("4. Graph & Routing", "CircuitDag.from_circuit (100x500 random circuit, 28k ops)", 120.0, "s", round(t_dag_rand, 4), "s")

    # cirq.decompose on 50k SWAPs (224k ops)
    qs_swap = [cirq.LineQubit(i) for i in range(1000)]
    c_swap = cirq.Circuit(cirq.SWAP(qs_swap[i], qs_swap[i+1]) for i in range(0, 998, 2) for _ in range(50))
    t_decomp = measure_time(lambda: cirq.decompose(c_swap), number=2)
    record("4. Protocols & Transformers", "cirq.decompose (50,000 SWAP gates -> 224k ops)", 3.23, "s", round(t_decomp, 3), "s")

    # cirq.has_unitary on 100k calls
    h_gate = cirq.H
    t_has_u = measure_time(lambda: [cirq.has_unitary(h_gate) for _ in range(100000)], number=5)
    record("4. Protocols & Transformers", "cirq.has_unitary (100,000 queries)", 0.35, "s", round(t_has_u, 4), "s")

    # cirq.unitary on 100k calls
    t_u = measure_time(lambda: [cirq.unitary(h_gate) for _ in range(100000)], number=3)
    record("4. Protocols & Transformers", "cirq.unitary (100,000 queries)", 1.52, "s", round(t_u, 4), "s")

    # Parameter resolution sweep (1000q x 100 steps = 100k ops)
    sym_a = sympy.Symbol('a')
    qs_sym = [cirq.LineQubit(i) for i in range(1000)]
    c_param = cirq.Circuit(cirq.X(q)**sym_a for q in qs_sym)
    resolvers = [{'a': val} for val in range(100)]
    def run_sweep():
        for res in resolvers:
            cirq.resolve_parameters(c_param, res)
    t_sweep = measure_time(run_sweep, number=5) * 1000
    record("4. Protocols & Transformers", "cirq.resolve_parameters sweep (1,000q x 100 steps)", 546.8, "ms", round(t_sweep, 2), "ms")

    # align_left on 500x500 circuit (~125k ops)
    qs_500 = cirq.LineQubit.range(500)
    rng = np.random.default_rng(42)
    moments_500 = [cirq.Moment(cirq.X(qs_500[q]) for q in rng.choice(500, size=250, replace=False)) for _ in range(500)]
    c_align = cirq.Circuit(moments_500)
    t_align = measure_time(lambda: cirq.align_left(c_align), number=3)
    record("4. Protocols & Transformers", "cirq.align_left (500x500 circuit, 125,000 ops)", 1.75, "s", round(t_align, 4), "s")


    print("\n=== 5. Memory Footprint ===")

    # 1,000,000 Operations Peak Memory (1,000 Qubits x 1,000 Moments)
    gc.collect()
    tracemalloc.start()
    qs_mem = [cirq.GridQubit(i, j) for i in range(50) for j in range(20)]
    c_1m = cirq.Circuit(cirq.Moment([cirq.X(q) for q in qs_mem]) for _ in range(1000))
    _, peak_1m_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_1m_mb = peak_1m_mem / (1024 * 1024)
    record("5. Memory Footprint", "Peak Memory (1,000 Qubits x 1,000 Moments = 1M ops)", 448.66, "MB", round(peak_1m_mb, 2), "MB")

    # Save to JSON
    with open("benchmarks/all_benchmark_results.json", "w") as fp:
        json.dump(results, fp, indent=2)
    print("\nSaved full benchmark results to benchmarks/all_benchmark_results.json")
    return results

if __name__ == "__main__":
    run_benchmarks()
