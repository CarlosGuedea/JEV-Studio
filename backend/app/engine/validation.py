"""Graph validation.

Checks performed before any execution:
  1. node ids unique; edge endpoints reference existing nodes
  2. exactly one Input node
  3. at least one Output node
  4. no unknown node types
  5. acyclic (topological sort also yields the execution order)
"""
from ..schemas import NodeType, WorkflowDefinition
from ..nodes import registry


class GraphValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_graph(defn: WorkflowDefinition) -> list[str]:
    """Returns the topological execution order (inputs first).
    Raises GraphValidationError with all detected problems."""
    errors: list[str] = []

    ids = [n.id for n in defn.nodes]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate node ids exist")

    node_by_id = {n.id: n for n in defn.nodes}
    known = registry()

    for node in defn.nodes:
        if node.type not in [NodeType(t) for t in known.keys()]:
            errors.append(f"Node '{node.id}' has unknown type '{node.type}'")
        # config must validate against its schema
        try:
            node.parsed_config()
        except Exception as exc:
            errors.append(f"Node '{node.id}': invalid config ({exc})")

    for edge in defn.edges:
        if edge.source not in node_by_id:
            errors.append(f"Edge '{edge.id}': source '{edge.source}' does not exist")
        if edge.target not in node_by_id:
            errors.append(f"Edge '{edge.id}': target '{edge.target}' does not exist")

    inputs = [n for n in defn.nodes if n.type == NodeType.INPUT]
    if len(inputs) == 0:
        errors.append("The workflow needs exactly one Input node (none found)")
    elif len(inputs) > 1:
        errors.append(f"The workflow needs exactly one Input node ({len(inputs)} found)")

    if not any(n.type == NodeType.OUTPUT for n in defn.nodes):
        errors.append("The workflow needs at least one Output node")

    order = topological_order(defn)  # raises on cycles
    if errors:
        raise GraphValidationError(errors)
    return order


def topological_order(defn: WorkflowDefinition) -> list[str]:
    """Kahn's algorithm; raises GraphValidationError on cycles."""
    indeg: dict[str, int] = {n.id: 0 for n in defn.nodes}
    adj: dict[str, list[str]] = {n.id: [] for n in defn.nodes}
    for e in defn.edges:
        if e.source in adj and e.target in indeg:
            adj[e.source].append(e.target)
            indeg[e.target] += 1

    queue = [n.id for n in defn.nodes if indeg[n.id] == 0]
    order: list[str] = []
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for nxt in adj[nid]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)

    if len(order) != len(defn.nodes):
        remaining = [nid for nid, d in indeg.items() if d > 0]
        raise GraphValidationError([f"Cycle detected involving nodes: {', '.join(remaining)}"])
    return order
