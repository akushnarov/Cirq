# Copyright 2018 The Cirq Developers
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

import functools
from collections.abc import Callable, Iterator
from typing import Any, cast, Generic, TypeVar

import networkx

import cirq
from cirq import ops

T = TypeVar('T')


@functools.total_ordering
class Unique(Generic[T]):
    """A wrapper for a value that doesn't compare equal to other instances.

    For example: 5 == 5 but Unique(5) != Unique(5).

    Unique is used by CircuitDag to wrap operations because nodes in a graph
    are considered the same node if they compare equal to each other.  For
    example, `X(q0)` in one moment of a circuit, and `X(q0)` in another moment
    of the circuit are wrapped by `cirq.Unique(X(q0))` so they are distinct
    nodes in the graph.
    """

    __slots__ = ('val',)

    def __init__(self, val: T) -> None:
        self.val = val

    def __repr__(self) -> str:
        return f'cirq.Unique({id(self)}, {self.val!r})'

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return id(self) < id(other)


def _disjoint_qubits(op1: cirq.Operation, op2: cirq.Operation) -> bool:
    """Returns true only if the operations have qubits in common."""
    return not set(op1.qubits) & set(op2.qubits)


class CircuitDag(networkx.DiGraph):
    """A representation of a Circuit as a directed acyclic graph.

    Nodes of the graph are instances of Unique containing each operation of a
    circuit.

    Edges of the graph are tuples of nodes.  Each edge specifies a required
    application order between two operations.  The first must be applied before
    the second.

    The graph is constructed as a transitive-minimal frontier dependency graph in linear O(N) time.
    """

    disjoint_qubits = staticmethod(_disjoint_qubits)

    def __init__(
        self,
        incoming_graph_data: Any = None,
        *,
        can_reorder: Callable[[cirq.Operation, cirq.Operation], bool] = _disjoint_qubits,
    ) -> None:
        """Initializes a CircuitDag.

        Args:
            incoming_graph_data: Data to initialize the graph.  This can be any
                value supported by networkx.DiGraph() e.g. an edge list or
                another graph.
            can_reorder: A predicate that determines if two operations may be
                reordered.  Graph edges are created for pairs of operations
                where this returns False.

                The default predicate allows reordering only when the operations
                don't share common qubits.
        """
        super().__init__(incoming_graph_data)
        self.can_reorder = can_reorder
        self._last_node_on_qubit: dict[cirq.Qid, Unique[cirq.Operation]] = {}
        self._last_node_on_mkey: dict[Any, Unique[cirq.Operation]] = {}
        if incoming_graph_data is not None and isinstance(incoming_graph_data, CircuitDag):
            self._last_node_on_qubit.update(incoming_graph_data._last_node_on_qubit)
            self._last_node_on_mkey.update(incoming_graph_data._last_node_on_mkey)

    @staticmethod
    def make_node(op: cirq.Operation) -> Unique[cirq.Operation]:
        return Unique(op)

    @staticmethod
    def from_circuit(
        circuit: cirq.Circuit,
        can_reorder: Callable[[cirq.Operation, cirq.Operation], bool] = _disjoint_qubits,
    ) -> CircuitDag:
        return CircuitDag.from_ops(circuit.all_operations(), can_reorder=can_reorder)

    @staticmethod
    def from_ops(
        *operations: cirq.OP_TREE,
        can_reorder: Callable[[cirq.Operation, cirq.Operation], bool] = _disjoint_qubits,
    ) -> CircuitDag:
        dag = CircuitDag(can_reorder=can_reorder)
        if can_reorder is _disjoint_qubits or can_reorder == _disjoint_qubits:
            last_on_qubit = dag._last_node_on_qubit
            last_on_mkey = dag._last_node_on_mkey
            make_node = dag.make_node
            add_node = dag.add_node
            add_edge = dag.add_edge
            for op in ops.flatten_op_tree(operations):
                op = cast(ops.Operation, op)
                new_node = make_node(op)
                add_node(new_node)
                for q in op.qubits:
                    pred = last_on_qubit.get(q)
                    if pred is not None:
                        add_edge(pred, new_node)
                    last_on_qubit[q] = new_node
                c_keys = cirq.control_keys(op)
                if c_keys:
                    for k in c_keys:
                        pred = last_on_mkey.get(k)
                        if pred is not None:
                            add_edge(pred, new_node)
                m_keys = cirq.measurement_key_objs(op)
                if m_keys:
                    for k in m_keys:
                        pred = last_on_mkey.get(k)
                        if pred is not None:
                            add_edge(pred, new_node)
                        last_on_mkey[k] = new_node
        else:
            for op in ops.flatten_op_tree(operations):
                dag.append(cast(ops.Operation, op))
        return dag

    def append(self, op: cirq.Operation) -> None:
        new_node = self.make_node(op)
        self.add_node(new_node)
        if self.can_reorder is _disjoint_qubits or self.can_reorder == _disjoint_qubits:
            for q in op.qubits:
                pred = self._last_node_on_qubit.get(q)
                if pred is not None:
                    self.add_edge(pred, new_node)
                self._last_node_on_qubit[q] = new_node
            c_keys = cirq.control_keys(op)
            if c_keys:
                for k in c_keys:
                    pred = self._last_node_on_mkey.get(k)
                    if pred is not None:
                        self.add_edge(pred, new_node)
            m_keys = cirq.measurement_key_objs(op)
            if m_keys:
                for k in m_keys:
                    pred = self._last_node_on_mkey.get(k)
                    if pred is not None:
                        self.add_edge(pred, new_node)
                    self._last_node_on_mkey[k] = new_node
        else:
            for node in list(self.nodes()):
                if node is not new_node and not self.can_reorder(node.val, op):
                    self.add_edge(node, new_node)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CircuitDag):
            return NotImplemented
        g1 = self.copy()
        g2 = other.copy()
        for node, attr in g1.nodes(data=True):
            attr['val'] = node.val
        for node, attr in g2.nodes(data=True):
            attr['val'] = node.val

        def node_match(attr1: dict[Any, Any], attr2: dict[Any, Any]) -> bool:
            return attr1['val'] == attr2['val']

        return networkx.is_isomorphic(g1, g2, node_match=node_match)

    def __ne__(self, other: Any) -> bool:
        return not self == other

    __hash__ = None  # type: ignore[assignment]

    def ordered_nodes(self) -> Iterator[Unique[cirq.Operation]]:
        if not self.nodes():
            return
        g = self.copy()

        def get_root_node(some_node: Unique[cirq.Operation]) -> Unique[cirq.Operation]:
            pred = g.pred
            while pred[some_node]:
                some_node = next(iter(pred[some_node]))
            return some_node

        def get_first_node() -> Unique[cirq.Operation]:
            return get_root_node(next(iter(g.nodes())))

        def get_next_node(succ: networkx.classes.coreviews.AtlasView) -> Unique[cirq.Operation]:
            if succ:
                return get_root_node(next(iter(succ)))

            return get_first_node()

        node = get_first_node()
        while True:
            yield node
            succ = g.succ[node]
            g.remove_node(node)

            if not g.nodes():
                return

            node = get_next_node(succ)

    def all_operations(self) -> Iterator[cirq.Operation]:
        return (node.val for node in self.ordered_nodes())

    def all_qubits(self) -> frozenset[cirq.Qid]:
        return frozenset(q for node in self.nodes for q in node.val.qubits)

    def to_circuit(self) -> cirq.Circuit:
        return cirq.Circuit(self.all_operations(), strategy=cirq.InsertStrategy.EARLIEST)

    def findall_nodes_until_blocked(
        self, is_blocker: Callable[[cirq.Operation], bool]
    ) -> Iterator[Unique[cirq.Operation]]:
        """Finds all nodes before blocking ones.

        Args:
            is_blocker: The predicate that indicates whether or not an
            operation is blocking.
        """
        remaining_dag = self.copy()

        for node in self.ordered_nodes():
            if node not in remaining_dag:
                continue
            if is_blocker(node.val):
                descendants = networkx.descendants(remaining_dag, node)
                remaining_dag.remove_nodes_from(descendants)
                remaining_dag.remove_node(node)
                continue
            yield node
