"""Safe expression evaluator for the Python and Condition nodes.

Security: arbitrary code is NEVER executed. The expression is parsed into an
AST and evaluated node-by-node against a strict whitelist — no imports, no
attribute access, no calls to unknown functions, no name rebinding tricks.
"""
import ast
import operator
from typing import Any


class UnsafeExpressionError(ValueError):
    pass


_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Not: operator.not_}
_CMP_OPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
    ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
}
_FUNCTIONS: dict[str, Any] = {
    "len": len, "abs": abs, "min": min, "max": max, "sum": sum,
    "round": round, "int": int, "float": float, "str": str, "bool": bool,
    "sorted": sorted, "list": list, "dict": dict, "set": set, "tuple": tuple,
    "any": any, "all": all, "enumerate": enumerate, "zip": zip,
    "startswith": lambda s, p: str(s).startswith(p),
    "endswith": lambda s, p: str(s).endswith(p),
    "lower": lambda s: str(s).lower(),
    "upper": lambda s: str(s).upper(),
    "contains": lambda container, item: item in container,
    "join": lambda sep, items: str(sep).join(str(i) for i in items),
    "split": lambda s, sep=None: str(s).split(sep),
    "keys": lambda d: list(dict(d).keys()),
    "values": lambda d: list(dict(d).values()),
    "get": lambda d, k, default=None: dict(d).get(k, default),
}
_MAX_NODES = 500


class _Evaluator(ast.NodeVisitor):
    def __init__(self, variables: dict[str, Any]) -> None:
        self.variables = variables
        self._nodes = 0

    def _count(self) -> None:
        self._nodes += 1
        if self._nodes > _MAX_NODES:
            raise UnsafeExpressionError("expression is too large")

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        self._count()
        if isinstance(node.value, (int, float, str, bool, type(None))):
            return node.value
        raise UnsafeExpressionError(f"constant not allowed: {type(node.value).__name__}")

    def visit_Name(self, node: ast.Name) -> Any:
        self._count()
        if node.id in self.variables:
            return self.variables[node.id]
        if node.id in _FUNCTIONS:
            return self.variables.get(node.id, _FUNCTIONS[node.id])
        raise UnsafeExpressionError(f"unknown name: {node.id}")

    def visit_List(self, node: ast.List) -> list:
        self._count()
        return [self.visit(e) for e in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> tuple:
        self._count()
        return tuple(self.visit(e) for e in node.elts)

    def visit_Dict(self, node: ast.Dict) -> dict:
        self._count()
        return {self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values)}

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        self._count()
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise UnsafeExpressionError(f"operator not allowed: {type(node.op).__name__}")
        return op(self.visit(node.left), self.visit(node.right))

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        self._count()
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise UnsafeExpressionError("unary operator not allowed")
        return op(self.visit(node.operand))

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        self._count()
        if isinstance(node.op, ast.And):
            result = True
            for v in node.values:
                result = self.visit(v)
                if not result:
                    return result
            return result
        if isinstance(node.op, ast.Or):
            for v in node.values:
                result = self.visit(v)
                if result:
                    return result
            return result
        raise UnsafeExpressionError("boolean operator not allowed")

    def visit_Compare(self, node: ast.Compare) -> bool:
        self._count()
        left = self.visit(node.left)
        for op_node, comparator in zip(node.ops, node.comparators):
            op = _CMP_OPS.get(type(op_node))
            if op is None:
                raise UnsafeExpressionError(f"comparison not allowed: {type(op_node).__name__}")
            right = self.visit(comparator)
            if not op(left, right):
                return False
            left = right
        return True

    def visit_IfExp(self, node: ast.IfExp) -> Any:
        self._count()
        return self.visit(node.body) if self.visit(node.test) else self.visit(node.orelse)

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        self._count()
        value = self.visit(node.value)
        key = self.visit(node.slice)
        if isinstance(value, (str, bytes, list, tuple, dict)):
            return value[key]
        raise UnsafeExpressionError("subscript only allowed on str/list/tuple/dict")

    def visit_Slice(self, node: ast.Slice) -> slice:
        self._count()
        return slice(
            self.visit(node.lower) if node.lower else None,
            self.visit(node.upper) if node.upper else None,
            self.visit(node.step) if node.step else None,
        )

    def visit_Call(self, node: ast.Call) -> Any:
        self._count()
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise UnsafeExpressionError("only whitelisted function calls are allowed")
        if node.keywords:
            raise UnsafeExpressionError("keyword arguments are not allowed")
        args = [self.visit(a) for a in node.args]
        return _FUNCTIONS[node.func.id](*args)

    def generic_visit(self, node: ast.AST) -> Any:
        raise UnsafeExpressionError(f"syntax not allowed: {type(node).__name__}")


def evaluate_expression(expression: str, variables: dict[str, Any]) -> Any:
    """Evaluate a whitelisted expression. Raises UnsafeExpressionError on
    anything that is not a pure, side-effect-free computation."""
    if len(expression) > 4_000:
        raise UnsafeExpressionError("expression exceeds 4000 characters")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpressionError(f"syntax error: {exc.msg}") from exc
    return _Evaluator(variables).visit(tree)
