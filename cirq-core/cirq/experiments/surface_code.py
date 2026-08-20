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

"""Fast vectorized generators for rotated planar surface code quantum circuits."""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence

from cirq import circuits, devices, ops


DEFAULT_X_ORDER: tuple[tuple[int, int], ...] = ((1, 1), (1, -1), (-1, 1), (-1, -1))
DEFAULT_Z_ORDER: tuple[tuple[int, int], ...] = ((1, 1), (-1, 1), (1, -1), (-1, -1))


@dataclasses.dataclass(frozen=True)
class SurfaceCodePatch:
    """Metadata and qubit coordinate layout for a rotated planar surface code patch.

    Attributes:
        distance: The code distance d of the rotated surface code (typically odd).
        data_qubits: Tuple of d*d data qubits on the (2x+1, 2y+1) subgrid.
        z_measure_qubits: Tuple of syndrome measurement qubits for Z stabilizers.
        x_measure_qubits: Tuple of syndrome measurement qubits for X stabilizers.
    """

    distance: int
    data_qubits: tuple[devices.GridQubit, ...]
    z_measure_qubits: tuple[devices.GridQubit, ...]
    x_measure_qubits: tuple[devices.GridQubit, ...]

    @property
    def all_qubits(self) -> tuple[devices.GridQubit, ...]:
        """All qubits (data and measure) in the surface code patch."""
        return self.data_qubits + self.z_measure_qubits + self.x_measure_qubits

    @property
    def num_data_qubits(self) -> int:
        return len(self.data_qubits)

    @property
    def num_measure_qubits(self) -> int:
        return len(self.z_measure_qubits) + len(self.x_measure_qubits)

    @classmethod
    def from_distance(cls, distance: int) -> SurfaceCodePatch:
        """Constructs a `SurfaceCodePatch` layout for a given code distance."""
        if distance < 2:
            raise ValueError(f'Surface code distance must be >= 2, got {distance}')

        d = distance
        max_coord = 2 * d + 2
        grid = [[devices.GridQubit(r, c) for c in range(max_coord)] for r in range(max_coord)]

        data_qubits = tuple(grid[2 * x + 1][2 * y + 1] for x in range(d) for y in range(d))
        x_measure_qubits = tuple(
            grid[2 * x][2 * y] for x in range(1, d) for y in range(d + 1) if (x + y) % 2 == 1
        )
        z_measure_qubits = tuple(
            grid[2 * x][2 * y] for x in range(d + 1) for y in range(1, d) if (x + y) % 2 == 0
        )

        return cls(
            distance=distance,
            data_qubits=data_qubits,
            z_measure_qubits=z_measure_qubits,
            x_measure_qubits=x_measure_qubits,
        )


def rotated_surface_code_cycle(
    patch: SurfaceCodePatch | int,
    x_order: Sequence[tuple[int, int]] = DEFAULT_X_ORDER,
    z_order: Sequence[tuple[int, int]] = DEFAULT_Z_ORDER,
    cz_interactions: bool = False,
) -> circuits.Circuit:
    """Constructs a circuit for a single round of rotated memory Z surface code syndrome extraction.

    Args:
        patch: A `SurfaceCodePatch` instance or an integer code distance.
        x_order: Specifies the order in which the 2/4 data qubit neighbors of an X measure qubit
            should be processed across the 4 interaction steps.
        z_order: Specifies the order in which the 2/4 data qubit neighbors of a Z measure qubit
            should be processed across the 4 interaction steps.
        cz_interactions: If True, uses CZ gates with Hadamard sandwiching rather than CNOT.

    Returns:
        A `cirq.Circuit` representing a single round of syndrome extraction.
    """
    if isinstance(patch, int):
        patch = SurfaceCodePatch.from_distance(patch)

    d = patch.distance
    max_coord = 2 * d + 2
    grid = [[devices.GridQubit(r, c) for c in range(max_coord)] for r in range(max_coord)]

    moments: list[circuits.Moment] = []

    # Step 0: Hadamard on all X measure qubits
    moments.append(circuits.Moment([ops.H(q) for q in patch.x_measure_qubits]))

    # Steps 1..4: 4-round entangling interaction schedule
    for k in range(4):
        x_dr, x_dc = x_order[k]
        z_dr, z_dc = z_order[k]
        step_ops: list[ops.Operation] = []

        for q in patch.x_measure_qubits:
            r, c = q.row + x_dr, q.col + x_dc
            if 0 < r < 2 * d and 0 < c < 2 * d:
                target_qubit = grid[r][c]
                step_ops.append(
                    ops.CZ(q, target_qubit) if cz_interactions else ops.CNOT(q, target_qubit)
                )

        for q in patch.z_measure_qubits:
            r, c = q.row + z_dr, q.col + z_dc
            if 0 < r < 2 * d and 0 < c < 2 * d:
                control_qubit = grid[r][c]
                step_ops.append(
                    ops.CZ(control_qubit, q) if cz_interactions else ops.CNOT(control_qubit, q)
                )

        moments.append(circuits.Moment(step_ops))

    # Step 5: Hadamard on all X measure qubits
    moments.append(circuits.Moment([ops.H(q) for q in patch.x_measure_qubits]))

    # Step 6: Measurement of all syndrome measure qubits
    moments.append(
        circuits.Moment(ops.measure_each(*patch.x_measure_qubits, *patch.z_measure_qubits))
    )

    return circuits.Circuit(moments)


def generate_rotated_surface_code_circuit(
    distance: int,
    num_rounds: int,
    as_subcircuit: bool = False,
    moment_by_moment: bool = True,
    x_order: Sequence[tuple[int, int]] = DEFAULT_X_ORDER,
    z_order: Sequence[tuple[int, int]] = DEFAULT_Z_ORDER,
    cz_interactions: bool = False,
) -> circuits.Circuit:
    """Generates a rotated memory Z planar surface code circuit.

    The circuit contains d*d data qubits and d**2 - 1 measure qubits, where d is the distance.
    Syndrome extraction is repeated across `num_rounds` cycles, followed by final transversal
    measurement of all data qubits.

    Args:
        distance: Distance of the surface code patch (e.g. 3, 5, 7, ..., 31).
        num_rounds: Number of error correction syndrome extraction rounds.
        as_subcircuit: If True, wraps the repetitive syndrome extraction cycle in a compressed
            `cirq.CircuitOperation` subcircuit with `use_repetition_ids=False`, achieving
            O(1) memory and construction time for large `num_rounds` (e.g. 100,000).
        moment_by_moment: If True, constructs the circuit layerwise from Moments. If False,
            constructs the circuit from the flat unrolled operation stream.
        x_order: Order of data qubit interactions for X measure qubits.
        z_order: Order of data qubit interactions for Z measure qubits.
        cz_interactions: If True, uses CZ entangling gates instead of CNOT.

    Returns:
        A `cirq.Circuit` for the rotated memory Z surface code experiment.
    """
    patch = SurfaceCodePatch.from_distance(distance)
    cycle = rotated_surface_code_cycle(
        patch=patch, x_order=x_order, z_order=z_order, cz_interactions=cz_interactions
    )

    final_meas_moment = circuits.Moment(ops.measure_each(*patch.data_qubits))

    if as_subcircuit:
        sub_op = circuits.CircuitOperation(
            cycle.freeze(), repetitions=num_rounds, use_repetition_ids=False
        )
        return circuits.Circuit(sub_op, final_meas_moment)

    if moment_by_moment:
        return circuits.Circuit(cycle * num_rounds, final_meas_moment)

    return circuits.Circuit(
        [*cycle.all_operations()] * num_rounds, ops.measure_each(*patch.data_qubits)
    )
