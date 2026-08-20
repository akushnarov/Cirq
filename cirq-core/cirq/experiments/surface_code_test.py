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

import collections
import pytest

import cirq
from cirq.experiments.surface_code import (
    SurfaceCodePatch,
    rotated_surface_code_cycle,
    generate_rotated_surface_code_circuit,
)


def test_surface_code_patch_creation() -> None:
    with pytest.raises(ValueError, match='Surface code distance must be >= 2'):
        SurfaceCodePatch.from_distance(1)

    patch_d3 = SurfaceCodePatch.from_distance(3)
    assert patch_d3.distance == 3
    assert patch_d3.num_data_qubits == 9
    assert patch_d3.num_measure_qubits == 8
    assert len(patch_d3.all_qubits) == 17
    assert len(patch_d3.z_measure_qubits) == 4
    assert len(patch_d3.x_measure_qubits) == 4

    patch_d5 = SurfaceCodePatch.from_distance(5)
    assert patch_d5.distance == 5
    assert patch_d5.num_data_qubits == 25
    assert patch_d5.num_measure_qubits == 24
    assert len(patch_d5.all_qubits) == 49


def test_rotated_surface_code_cycle() -> None:
    cycle_cnot = rotated_surface_code_cycle(3, cz_interactions=False)
    assert len(cycle_cnot) == 7
    # Verify moment structure: H, 4 interaction moments, H, Measure
    assert all(isinstance(op.gate, cirq.HPowGate) for op in cycle_cnot[0].operations)
    assert all(isinstance(op.gate, cirq.HPowGate) for op in cycle_cnot[5].operations)
    assert all(isinstance(op.gate, cirq.MeasurementGate) for op in cycle_cnot[6].operations)

    cycle_cz = rotated_surface_code_cycle(3, cz_interactions=True)
    assert len(cycle_cz) == 7
    # Verify CZ gates used in interaction moments
    for m in cycle_cz[1:5]:
        assert all(isinstance(op.gate, cirq.CZPowGate) for op in m.operations)


def test_generate_rotated_surface_code_circuit_moment_by_moment() -> None:
    c = generate_rotated_surface_code_circuit(3, num_rounds=9, moment_by_moment=True)
    # 9 rounds of 7 moments + 1 final measurement moment = 64 moments
    assert len(c) == 64
    assert sum(1 for _ in c.all_operations()) == 369


def test_generate_rotated_surface_code_circuit_operation_by_operation() -> None:
    c_obo = generate_rotated_surface_code_circuit(3, num_rounds=9, moment_by_moment=False)
    c_mbm = generate_rotated_surface_code_circuit(3, num_rounds=9, moment_by_moment=True)
    assert collections.Counter(c_obo.all_operations()) == collections.Counter(
        c_mbm.all_operations()
    )


def test_generate_rotated_surface_code_circuit_as_subcircuit() -> None:
    c_sub = generate_rotated_surface_code_circuit(3, num_rounds=9, as_subcircuit=True)
    assert len(c_sub) == 2  # 1 subcircuit operation + 1 final measurement moment

    sub_op = c_sub[0].operations[0]
    assert isinstance(sub_op, cirq.CircuitOperation)
    assert sub_op.repetitions == 9

    # Unroll CircuitOperation and compare operations with standard circuit
    c_unrolled = cirq.Circuit(
        cirq.decompose(c_sub, keep=lambda op: not isinstance(op, cirq.CircuitOperation))
    )
    c_expected = generate_rotated_surface_code_circuit(3, num_rounds=9, moment_by_moment=True)
    assert collections.Counter(c_unrolled.all_operations()) == collections.Counter(
        c_expected.all_operations()
    )


def test_generate_rotated_surface_code_circuit_large_rounds_subcircuit() -> None:
    # 100,000 rounds should construct in milliseconds and use O(1) moments
    c_large = generate_rotated_surface_code_circuit(15, num_rounds=100_000, as_subcircuit=True)
    assert len(c_large) == 2
    sub_op = c_large[0].operations[0]
    assert isinstance(sub_op, cirq.CircuitOperation)
    assert sub_op.repetitions == 100_000


def test_generate_rotated_surface_code_circuit_cz() -> None:
    c_cz = generate_rotated_surface_code_circuit(3, num_rounds=2, cz_interactions=True)
    assert any(isinstance(op.gate, cirq.CZPowGate) for op in c_cz.all_operations())
