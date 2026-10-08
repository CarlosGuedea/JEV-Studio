"""Graph validation tests."""
import pytest

from app.engine.validation import GraphValidationError, validate_graph
from app.schemas import WorkflowDefinition


def make(nodes, edges):
    return WorkflowDefinition.model_validate({
        "nodes": nodes,
        "edges": edges,
        "config": {"name": "test"},
    })


def n(nid, ntype, **cfg):
    return {"id": nid, "type": ntype, "position": {"x": 0, "y": 0}, "config": cfg}


VALID = make(
    [
        n("in", "input"),
        n("d", "jev_decision", options=["A", "B"]),
        n("out_a", "output"),
        n("out_b", "output"),
    ],
    [
        {"id": "e1", "source": "in", "target": "d"},
        {"id": "e2", "source": "d", "target": "out_a", "label": "A"},
        {"id": "e3", "source": "d", "target": "out_b", "label": "B"},
    ],
)


def test_valid_graph_returns_topological_order():
    order = validate_graph(VALID)
    assert order.index("in") < order.index("d")
    assert order.index("d") < order.index("out_a")


def test_missing_input_rejected():
    bad = make([n("d", "jev_decision", options=["A"])], [])
    with pytest.raises(GraphValidationError) as exc:
        validate_graph(bad)
    assert "Input" in str(exc.value)


def test_missing_output_rejected():
    bad = make([n("in", "input")], [])
    with pytest.raises(GraphValidationError):
        validate_graph(bad)


def test_unknown_node_type_rejected():
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc:
        make([n("in", "input"), n("x", "not_a_type"), n("out", "output")],
             [{"id": "e1", "source": "in", "target": "x"},
              {"id": "e2", "source": "x", "target": "out"}])
    assert "not_a_type" in str(exc.value)


def test_dangling_edge_rejected():
    bad = make([n("in", "input"), n("out", "output")],
               [{"id": "e1", "source": "in", "target": "ghost"}])
    with pytest.raises(GraphValidationError):
        validate_graph(bad)


def test_cycle_detected():
    bad = make(
        [n("in", "input"), n("a", "python"), n("b", "python"), n("out", "output")],
        [{"id": "e1", "source": "in", "target": "a"},
         {"id": "e2", "source": "a", "target": "b"},
         {"id": "e3", "source": "b", "target": "a"},
         {"id": "e4", "source": "b", "target": "out"}],
    )
    with pytest.raises(GraphValidationError) as exc:
        validate_graph(bad)
    assert "Cycle" in str(exc.value)


def test_invalid_config_rejected():
    bad = make([n("in", "input"), n("d", "jev_decision", options=[]), n("out", "output")],
               [{"id": "e1", "source": "in", "target": "d"},
                {"id": "e2", "source": "d", "target": "out"}])
    # empty options is allowed by the schema itself; use a bad field type instead
    bad.nodes[1].config = {"options": "not-a-list"}
    with pytest.raises(GraphValidationError):
        validate_graph(bad)
