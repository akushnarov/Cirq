# Copyright 2022 The Cirq Developers
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

"""Transformer passes which align operations to the left or right of the circuit."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from cirq import circuits, ops, protocols
from cirq.transformers import transformer_api, transformer_primitives

if TYPE_CHECKING:
    import cirq


@transformer_api.transformer(add_deep_support=True)
def align_left(
    circuit: cirq.AbstractCircuit, *, context: cirq.TransformerContext | None = None
) -> cirq.Circuit:
    """Aligns gates to the left of the circuit.

    Note that tagged operations with tag in `context.tags_to_ignore` will continue to stay in their
    original position and will not be aligned.

    Args:
          circuit: Input circuit to transform.
          context: `cirq.TransformerContext` storing common configurable options for transformers.

    Returns:
          Copy of the transformed input circuit.
    """
    if context is None:
        context = transformer_api.TransformerContext()

    tags_to_ignore = set(context.tags_to_ignore) if context.tags_to_ignore else ()

    qubit_indices: dict[cirq.Qid, int] = {}
    mkey_indices: dict[cirq.MeasurementKey, int] = {}
    ckey_indices: dict[cirq.MeasurementKey, int] = {}
    moments_ops: list[list[cirq.Operation]] = []

    for i, moment in enumerate(circuit):
        for op in moment:
            if (
                tags_to_ignore
                and isinstance(op, ops.TaggedOperation)
                and not tags_to_ignore.isdisjoint(op.tags)
            ):
                target_idx = i
                while len(moments_ops) <= target_idx:
                    moments_ops.append([])
                moments_ops[target_idx].append(op)

                for q in op.qubits:
                    qubit_indices[q] = target_idx
                mkeys = protocols.measurement_key_objs(op)
                if mkeys:
                    for k in mkeys:
                        mkey_indices[k] = target_idx
                ckeys = protocols.control_keys(op)
                if ckeys:
                    for k in ckeys:
                        prev = ckey_indices.get(k, -1)
                        if target_idx > prev:
                            ckey_indices[k] = target_idx
            else:
                last_conflict = -1
                op_qubits = op.qubits
                n_qubits = len(op_qubits)
                if n_qubits == 1:
                    last_conflict = qubit_indices.get(op_qubits[0], -1)
                elif n_qubits == 2:
                    i0 = qubit_indices.get(op_qubits[0], -1)
                    i1 = qubit_indices.get(op_qubits[1], -1)
                    last_conflict = max(i1, i0)
                elif n_qubits > 2:
                    for q in op_qubits:
                        idx = qubit_indices.get(q, -1)
                        last_conflict = max(last_conflict, idx)

                mkeys = protocols.measurement_key_objs(op)
                if mkeys:
                    for k in mkeys:
                        idx = mkey_indices.get(k, -1)
                        last_conflict = max(last_conflict, idx)
                        idx = ckey_indices.get(k, -1)
                        last_conflict = max(last_conflict, idx)
                ckeys = protocols.control_keys(op)
                if ckeys:
                    for k in ckeys:
                        idx = mkey_indices.get(k, -1)
                        last_conflict = max(last_conflict, idx)

                target_idx = last_conflict + 1
                while len(moments_ops) <= target_idx:
                    moments_ops.append([])
                moments_ops[target_idx].append(op)

                if n_qubits == 1:
                    qubit_indices[op_qubits[0]] = target_idx
                elif n_qubits == 2:
                    qubit_indices[op_qubits[0]] = target_idx
                    qubit_indices[op_qubits[1]] = target_idx
                elif n_qubits > 2:
                    for q in op_qubits:
                        qubit_indices[q] = target_idx

                if mkeys:
                    for k in mkeys:
                        mkey_indices[k] = target_idx
                if ckeys:
                    for k in ckeys:
                        prev = ckey_indices.get(k, -1)
                        if target_idx > prev:
                            ckey_indices[k] = target_idx

    return circuits.Circuit._from_moments(
        [circuits.Moment(m) for m in moments_ops], tags=circuit.tags
    )


@transformer_api.transformer(add_deep_support=True)
def align_right(
    circuit: cirq.AbstractCircuit, *, context: cirq.TransformerContext | None = None
) -> cirq.Circuit:
    """Aligns gates to the right of the circuit.

    Note that tagged operations with tag in `context.tags_to_ignore` will continue to stay in their
    original position and will not be aligned.

    Args:
          circuit: Input circuit to transform.
          context: `cirq.TransformerContext` storing common configurable options for transformers.

    Returns:
          Copy of the transformed input circuit.
    """
    if context is not None and context.deep is True:
        context = dataclasses.replace(context, deep=False)
    # Reverse the circuit, align left, and reverse again. Note each moment also has to have its ops
    # reversed internally, to avoid edge conditions where non-commuting but can-be-in-same-moment
    # ops (measurements and classical controls, particularly) could end up getting swapped.
    backwards = transformer_primitives.reverse_circuit(circuit)
    aligned_backwards = align_left(backwards, context=context)
    return transformer_primitives.reverse_circuit(aligned_backwards)
