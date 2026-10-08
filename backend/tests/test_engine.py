"""Engine execution tests: linear runs, branching, errors, skipping."""
from app.engine.runner import run_workflow
from app.schemas import WorkflowDefinition


def make(nodes, edges, variables=None):
    return WorkflowDefinition.model_validate({
        "nodes": nodes,
        "edges": edges,
        "config": {"name": "test"},
        "variables": variables or {},
    })


def n(nid, ntype, **cfg):
    return {"id": nid, "type": ntype, "position": {"x": 0, "y": 0}, "config": cfg}


def statuses(result):
    return {s.node_id: s.status.value for s in result.steps}


def test_linear_execution():
    wf = make(
        [n("in", "input"), n("py", "python", expression="len(split(input))"), n("out", "output")],
        [{"id": "e1", "source": "in", "target": "py"},
         {"id": "e2", "source": "py", "target": "out"}],
    )
    result = run_workflow(wf, user_input="uno dos tres")
    assert result.status.value == "SUCCESS"
    st = statuses(result)
    assert all(v == "SUCCESS" for v in st.values())
    assert result.output["value"]["result"] == 3


def test_branching_only_runs_selected_path():
    # mock provider: "python" in context selects PYTHON
    wf = make(
        [n("in", "input"),
         n("d", "jev_decision", options=["PYTHON", "LLM"]),
         n("py", "python", expression="'py:' + str(len(data))"),
         n("llm", "python", expression="'llm'"),
         n("out", "output")],
        [{"id": "e1", "source": "in", "target": "d"},
         {"id": "e2", "source": "d", "target": "py", "label": "PYTHON"},
         {"id": "e3", "source": "d", "target": "llm", "label": "LLM"},
         {"id": "e4", "source": "py", "target": "out"},
         {"id": "e5", "source": "llm", "target": "out"}],
    )
    result = run_workflow(wf, user_input="procesa esto con python")
    st = statuses(result)
    assert st["d"] == "SUCCESS"
    assert st["py"] == "SUCCESS"
    assert st["llm"] == "SKIPPED"
    assert st["out"] == "SUCCESS"
    assert result.output["value"]["result"].startswith("py:")


def test_error_stops_branch_and_marks_execution_error():
    wf = make(
        [n("in", "input"),
         n("boom", "python", expression="1/0"),
         n("after", "python", expression="1"),
         n("out", "output")],
        [{"id": "e1", "source": "in", "target": "boom"},
         {"id": "e2", "source": "boom", "target": "after"},
         {"id": "e3", "source": "after", "target": "out"}],
    )
    result = run_workflow(wf, user_input="x")
    st = statuses(result)
    assert st["boom"] == "ERROR"
    assert st["after"] == "SKIPPED"
    assert st["out"] == "SKIPPED"
    assert result.status.value == "ERROR"
    assert "ZeroDivisionError" in result.error


def test_condition_branching():
    wf = make(
        [n("in", "input"),
         n("d", "jev_decision", options=["PYTHON"]),
         n("cond", "condition", expression="confidence > 0.5"),
         n("yes", "python", expression="'yes'"),
         n("no", "python", expression="'no'"),
         n("out", "output")],
        [{"id": "e1", "source": "in", "target": "d"},
         {"id": "e2", "source": "d", "target": "cond"},
         {"id": "e3", "source": "cond", "target": "yes", "label": "true"},
         {"id": "e4", "source": "cond", "target": "no", "label": "false"},
         {"id": "e5", "source": "yes", "target": "out"},
         {"id": "e6", "source": "no", "target": "out"}],
    )
    result = run_workflow(wf, user_input="python por favor")
    st = statuses(result)
    assert st["cond"] == "SUCCESS"
    assert result.output["value"]["result"] == "yes"
    assert st["no"] == "SKIPPED"


def test_unreachable_node_is_skipped():
    wf = make(
        [n("in", "input"), n("lonely", "python", expression="1"), n("out", "output")],
        [{"id": "e1", "source": "in", "target": "out"}],
    )
    result = run_workflow(wf, user_input="x")
    assert statuses(result)["lonely"] == "SKIPPED"


def test_demo_workflow_executes():
    from app.services.demo import demo_definition
    result = run_workflow(demo_definition(), user_input="cuenta palabras con python")
    assert result.status.value == "SUCCESS"
    st = statuses(result)
    assert st["n_py"] == "SUCCESS"
    assert st["n_sql"] == "SKIPPED"
    assert st["n_llm"] == "SKIPPED"
