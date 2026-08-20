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

from __future__ import annotations

import collections

import cirq


def test_align_basic_no_context() -> None:
    q1 = cirq.NamedQubit('q1')
    q2 = cirq.NamedQubit('q2')
    c = cirq.Circuit(
        [
            cirq.Moment([cirq.X(q1)]),
            cirq.Moment([cirq.Y(q1), cirq.X(q2)]),
            cirq.Moment([cirq.X(q1)]),
        ]
    )
    cirq.testing.assert_same_circuits(
        cirq.align_left(c),
        cirq.Circuit(
            cirq.Moment([cirq.X(q1), cirq.X(q2)]),
            cirq.Moment([cirq.Y(q1)]),
            cirq.Moment([cirq.X(q1)]),
        ),
    )
    cirq.testing.assert_same_circuits(
        cirq.align_right(c),
        cirq.Circuit(
            cirq.Moment([cirq.X(q1)]),
            cirq.Moment([cirq.Y(q1)]),
            cirq.Moment([cirq.X(q1), cirq.X(q2)]),
        ),
    )


def test_align_left_no_compile_context() -> None:
    q1 = cirq.NamedQubit('q1')
    q2 = cirq.NamedQubit('q2')
    cirq.testing.assert_same_circuits(
        cirq.align_left(
            cirq.Circuit(
                [
                    cirq.Moment([cirq.X(q1)]),
                    cirq.Moment([cirq.Y(q1), cirq.X(q2)]),
                    cirq.Moment([cirq.X(q1), cirq.Y(q2).with_tags("nocompile")]),
                    cirq.Moment([cirq.Y(q1)]),
                    cirq.measure(*[q1, q2], key='a'),
                ]
            ),
            context=cirq.TransformerContext(tags_to_ignore=("nocompile",)),
        ),
        cirq.Circuit(
            [
                cirq.Moment([cirq.X(q1), cirq.X(q2)]),
                cirq.Moment([cirq.Y(q1)]),
                cirq.Moment([cirq.X(q1), cirq.Y(q2).with_tags("nocompile")]),
                cirq.Moment([cirq.Y(q1)]),
                cirq.measure(*[q1, q2], key='a'),
            ]
        ),
    )


def test_align_left_deep() -> None:
    q1, q2 = cirq.LineQubit.range(2)
    c_nested = cirq.FrozenCircuit(
        [
            cirq.Moment([cirq.X(q1)]),
            cirq.Moment([cirq.Y(q2)]),
            cirq.Moment([cirq.Z(q1), cirq.Y(q2).with_tags("nocompile")]),
            cirq.Moment([cirq.Y(q1)]),
            cirq.measure(q2, key='a'),
            cirq.Z(q1).with_classical_controls('a'),
        ]
    )
    c_nested_aligned = cirq.FrozenCircuit(
        cirq.Moment(cirq.X(q1), cirq.Y(q2)),
        cirq.Moment(cirq.Z(q1)),
        cirq.Moment([cirq.Y(q1), cirq.Y(q2).with_tags("nocompile")]),
        cirq.measure(q2, key='a'),
        cirq.Z(q1).with_classical_controls('a'),
    )
    c_orig = cirq.Circuit(
        c_nested,
        cirq.CircuitOperation(c_nested).repeat(6).with_tags("nocompile"),
        c_nested,
        cirq.CircuitOperation(c_nested).repeat(5).with_tags("preserve_tag"),
    )
    c_expected = cirq.Circuit(
        c_nested_aligned,
        cirq.CircuitOperation(c_nested).repeat(6).with_tags("nocompile"),
        c_nested_aligned,
        cirq.CircuitOperation(c_nested_aligned).repeat(5).with_tags("preserve_tag"),
    )
    context = cirq.TransformerContext(tags_to_ignore=("nocompile",), deep=True)
    cirq.testing.assert_same_circuits(cirq.align_left(c_orig, context=context), c_expected)


def test_align_left_subset_of_operations() -> None:
    q1 = cirq.NamedQubit('q1')
    q2 = cirq.NamedQubit('q2')
    tag = "op_to_align"
    c_orig = cirq.Circuit(
        [
            cirq.Moment([cirq.Y(q1)]),
            cirq.Moment([cirq.X(q2)]),
            cirq.Moment([cirq.X(q1).with_tags(tag)]),
            cirq.Moment([cirq.Y(q2)]),
            cirq.measure(*[q1, q2], key='a'),
        ]
    )
    c_exp = cirq.Circuit(
        [
            cirq.Moment([cirq.Y(q1)]),
            cirq.Moment([cirq.X(q1).with_tags(tag), cirq.X(q2)]),
            cirq.Moment(),
            cirq.Moment([cirq.Y(q2)]),
            cirq.measure(*[q1, q2], key='a'),
        ]
    )
    cirq.testing.assert_same_circuits(
        cirq.toggle_tags(
            cirq.align_left(
                cirq.toggle_tags(c_orig, [tag]),
                context=cirq.TransformerContext(tags_to_ignore=(tag,)),
            ),
            [tag],
        ),
        c_exp,
    )


def test_align_right_no_compile_context() -> None:
    q1 = cirq.NamedQubit('q1')
    q2 = cirq.NamedQubit('q2')
    cirq.testing.assert_same_circuits(
        cirq.align_right(
            cirq.Circuit(
                [
                    cirq.Moment([cirq.X(q1)]),
                    cirq.Moment([cirq.Y(q1), cirq.X(q2).with_tags("nocompile")]),
                    cirq.Moment([cirq.X(q1), cirq.Y(q2)]),
                    cirq.Moment([cirq.Y(q1)]),
                    cirq.measure(*[q1, q2], key='a'),
                ]
            ),
            context=cirq.TransformerContext(tags_to_ignore=("nocompile",)),
        ),
        cirq.Circuit(
            [
                cirq.Moment([cirq.X(q1)]),
                cirq.Moment([cirq.Y(q1), cirq.X(q2).with_tags("nocompile")]),
                cirq.Moment([cirq.X(q1)]),
                cirq.Moment([cirq.Y(q1), cirq.Y(q2)]),
                cirq.measure(*[q1, q2], key='a'),
            ]
        ),
    )


def test_align_right_deep() -> None:
    q1, q2 = cirq.LineQubit.range(2)
    c_nested = cirq.FrozenCircuit(
        cirq.Moment([cirq.X(q1)]),
        cirq.Moment([cirq.Y(q1), cirq.X(q2).with_tags("nocompile")]),
        cirq.Moment([cirq.X(q2)]),
        cirq.Moment([cirq.Y(q1)]),
        cirq.measure(q1, key='a'),
        cirq.Z(q2).with_classical_controls('a'),
    )
    c_nested_aligned = cirq.FrozenCircuit(
        cirq.Moment([cirq.X(q1), cirq.X(q2).with_tags("nocompile")]),
        [cirq.Y(q1), cirq.Y(q1)],
        cirq.Moment(cirq.measure(q1, key='a'), cirq.X(q2)),
        cirq.Z(q2).with_classical_controls('a'),
    )
    c_orig = cirq.Circuit(
        c_nested,
        cirq.CircuitOperation(c_nested).repeat(6).with_tags("nocompile"),
        c_nested,
        cirq.CircuitOperation(c_nested).repeat(5).with_tags("preserve_tag"),
    )
    c_expected = cirq.Circuit(
        c_nested_aligned,
        cirq.CircuitOperation(c_nested).repeat(6).with_tags("nocompile"),
        cirq.Moment(),
        c_nested_aligned,
        cirq.CircuitOperation(c_nested_aligned).repeat(5).with_tags("preserve_tag"),
    )
    context = cirq.TransformerContext(tags_to_ignore=("nocompile",), deep=True)
    cirq.testing.assert_same_circuits(cirq.align_right(c_orig, context=context), c_expected)


def test_classical_control() -> None:
    q0, q1 = cirq.LineQubit.range(2)
    circuit = cirq.Circuit(
        cirq.H(q0), cirq.measure(q0, key='m'), cirq.X(q1).with_classical_controls('m')
    )
    cirq.testing.assert_same_circuits(cirq.align_left(circuit), circuit)
    cirq.testing.assert_same_circuits(cirq.align_right(circuit), circuit)


def test_measurement_and_classical_control_same_moment_preserve_order() -> None:
    q0, q1 = cirq.LineQubit.range(2)
    circuit = cirq.Circuit()
    op_measure = cirq.measure(q0, key='m')
    op_controlled = cirq.X(q1).with_classical_controls('m')
    circuit.append(op_measure)
    circuit.append(op_controlled, cirq.InsertStrategy.INLINE)
    circuit = cirq.align_right(circuit)
    ops_in_order = list(circuit.all_operations())
    assert ops_in_order[0] == op_measure
    assert ops_in_order[1] == op_controlled


def test_align_empty_circuit() -> None:
    empty_c = cirq.Circuit()
    cirq.testing.assert_same_circuits(cirq.align_left(empty_c), empty_c)
    cirq.testing.assert_same_circuits(cirq.align_right(empty_c), empty_c)

    empty_moments_c = cirq.Circuit(cirq.Moment(), cirq.Moment())
    cirq.testing.assert_same_circuits(cirq.align_left(empty_moments_c), cirq.Circuit())
    cirq.testing.assert_same_circuits(cirq.align_right(empty_moments_c), cirq.Circuit())


def test_align_with_circuit_tags() -> None:
    q = cirq.LineQubit(0)
    c = cirq.Circuit(cirq.X(q), tags=('my_tag',))
    aligned_left = cirq.align_left(c)
    assert aligned_left.tags == ('my_tag',)
    aligned_right = cirq.align_right(c)
    assert aligned_right.tags == ('my_tag',)


def test_align_3qubit_gates() -> None:
    q0, q1, q2 = cirq.LineQubit.range(3)
    c = cirq.Circuit(
        cirq.Moment([cirq.X(q0)]), cirq.Moment([cirq.Y(q1)]), cirq.Moment([cirq.CCZ(q0, q1, q2)])
    )
    expected_left = cirq.Circuit(
        cirq.Moment([cirq.X(q0), cirq.Y(q1)]), cirq.Moment([cirq.CCZ(q0, q1, q2)])
    )
    cirq.testing.assert_same_circuits(cirq.align_left(c), expected_left)


def test_align_random_circuits_equivalence() -> None:
    for seed in range(5):
        c = cirq.testing.random_circuit(qubits=20, n_moments=30, op_density=0.6, random_state=seed)
        left = cirq.align_left(c)
        right = cirq.align_right(c)
        # Verify idempotency of alignment
        cirq.testing.assert_same_circuits(cirq.align_left(left), left)
        cirq.testing.assert_same_circuits(cirq.align_right(right), right)
        # Verify operations are preserved
        assert collections.Counter(c.all_operations()) == collections.Counter(left.all_operations())
        assert collections.Counter(c.all_operations()) == collections.Counter(
            right.all_operations()
        )


def test_align_with_ignored_tagged_classical_controls() -> None:
    q0, q1 = cirq.LineQubit.range(2)
    tag = 'ignore_me'
    c = cirq.Circuit(
        cirq.Moment([cirq.measure(q0, key='m')]),
        cirq.Moment(),
        cirq.Moment([cirq.X(q1).with_classical_controls('m').with_tags(tag)]),
    )
    context = cirq.TransformerContext(tags_to_ignore=(tag,))
    aligned = cirq.align_left(c, context=context)
    cirq.testing.assert_same_circuits(aligned, c)
