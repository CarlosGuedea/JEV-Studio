"""Node executors.

Each executor receives an ExecutionContext with:
  - config:      parsed Pydantic config for the node
  - node_id:     client-side node id
  - inputs:      list of outputs from active predecessor nodes
  - input_text:  concatenated text view of the inputs (for Jev `state`)
  - variables:   run-level variables (user input + extras)
  - outputs:     {node_id: output} of every completed node
and returns a JSON-serialisable dict. `branch` selects which outgoing edge
labels stay active for jev_decision / condition nodes.

To add a new node type: subclass NodeExecutor, implement execute(), and
register it in registry().
"""
import json
from abc import ABC, abstractmethod
from typing import Any

from ..schemas import (
    ConditionConfig,
    HttpRequestConfig,
    InputConfig,
    JevDecisionConfig,
    LLMConfig,
    OutputConfig,
    PythonConfig,
)
from .safe_eval import evaluate_expression


class ExecutionContext:
    def __init__(self, *, node_id: str, config: Any, inputs: list[Any],
                 variables: dict[str, Any], outputs: dict[str, Any]) -> None:
        self.node_id = node_id
        self.config = config
        self.inputs = inputs
        self.variables = variables
        self.outputs = outputs

    @property
    def input_text(self) -> str:
        parts: list[str] = []
        for value in self.inputs:
            if isinstance(value, str):
                parts.append(value)
            else:
                parts.append(json.dumps(value, ensure_ascii=False, default=str))
        return "\n".join(parts)


class NodeExecutor(ABC):
    node_type: str = "abstract"

    @abstractmethod
    def execute(self, ctx: ExecutionContext) -> dict[str, Any]:
        ...


class InputExecutor(NodeExecutor):
    node_type = "input"

    def execute(self, ctx: ExecutionContext) -> dict[str, Any]:
        cfg: InputConfig = ctx.config
        value = ctx.variables.get("input")
        return {
            "input": value,
            "message": cfg.message,
            "type": type(value).__name__,
        }


class JevDecisionExecutor(NodeExecutor):
    node_type = "jev_decision"

    def execute(self, ctx: ExecutionContext) -> dict[str, Any]:
        from ..providers import get_jev_provider

        cfg: JevDecisionConfig = ctx.config
        options = [o.strip() for o in cfg.options if o.strip()]
        if not options:
            raise ValueError("Jev Decision needs at least one option")

        context_parts = [cfg.instructions] if cfg.instructions else []
        context_parts.append(ctx.input_text or json.dumps(ctx.variables.get("input"), default=str))
        context = "\n".join(p for p in context_parts if p)

        provider = get_jev_provider(cfg.provider, model=cfg.model)
        decision = provider.decide(context, cfg.question, options)
        return {
            "selected": decision.selected,
            "confidence": decision.confidence,
            "simulated": decision.simulated,
            "provider": provider.name,
            "question": cfg.question,
            "options": options,
            "raw": decision.raw,
        }

    def branch(self, ctx: ExecutionContext, result: dict[str, Any]) -> set[str]:
        """Only the edge labelled with the selected option stays active."""
        return {str(result.get("selected", "")).strip().upper()}


class LLMExecutor(NodeExecutor):
    node_type = "llm"

    def execute(self, ctx: ExecutionContext) -> dict[str, Any]:
        from ..providers import registry, resolve_api_key

        cfg: LLMConfig = ctx.config
        prompt = render_template(cfg.prompt, ctx)
        system = render_template(cfg.system_prompt, ctx) if cfg.system_prompt else ""
        provider = registry().get(cfg.provider) or registry()["openai_compatible"]
        api_key = resolve_api_key(cfg.api_key_env)
        result = provider.chat(
            model=cfg.model, system=system, prompt=prompt,
            temperature=cfg.temperature, max_tokens=cfg.max_tokens,
            endpoint=cfg.endpoint or None, api_key=api_key,
        )
        return {"text": result.text, "raw": result.raw}


class PythonExecutor(NodeExecutor):
    node_type = "python"

    def execute(self, ctx: ExecutionContext) -> dict[str, Any]:
        cfg: PythonConfig = ctx.config
        data = ctx.inputs[0] if len(ctx.inputs) == 1 else ctx.inputs
        value = evaluate_expression(
            cfg.expression,
            {"data": data, "input": ctx.variables.get("input"), **ctx.variables},
        )
        return {"result": value, "expression": cfg.expression}


class HttpRequestExecutor(NodeExecutor):
    node_type = "http_request"

    def execute(self, ctx: ExecutionContext) -> dict[str, Any]:
        import httpx

        from ..config import get_settings

        cfg: HttpRequestConfig = ctx.config
        settings = get_settings()
        url = render_template(cfg.url, ctx)

        parsed = httpx.URL(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"URL scheme not allowed: {parsed.scheme!r} (only http/https)")
        allowed = settings.http_allowed_host_list
        if allowed and (parsed.host or "").lower() not in allowed:
            raise ValueError(f"host not in allowlist: {parsed.host}")

        timeout = min(cfg.timeout_seconds, settings.http_timeout_seconds)
        body = render_template(cfg.body, ctx) if isinstance(cfg.body, str) else cfg.body
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.request(cfg.method, url, headers=cfg.headers,
                                  json=body if body is not None else None)
            content = resp.text
        if len(content) > settings.http_max_response_bytes:
            raise RuntimeError("HTTP response exceeds the configured size limit")
        try:
            data: Any = resp.json()
        except Exception:
            data = content[: settings.http_max_response_bytes]
        return {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": data,
        }


class ConditionExecutor(NodeExecutor):
    node_type = "condition"

    def execute(self, ctx: ExecutionContext) -> dict[str, Any]:
        cfg: ConditionConfig = ctx.config
        previous = ctx.inputs[-1] if ctx.inputs else None
        variables = {
            "data": previous,
            "input": ctx.variables.get("input"),
            "confidence": _extract_confidence(previous),
            **ctx.variables,
            **ctx.outputs,
        }
        value = bool(evaluate_expression(cfg.expression, variables))
        return {"condition": cfg.expression, "result": value}

    def branch(self, ctx: ExecutionContext, result: dict[str, Any]) -> set[str]:
        return {"TRUE" if result.get("result") else "FALSE"}


class OutputExecutor(NodeExecutor):
    node_type = "output"

    def execute(self, ctx: ExecutionContext) -> dict[str, Any]:
        cfg: OutputConfig = ctx.config
        return {
            "label": cfg.label,
            "value": ctx.inputs[-1] if len(ctx.inputs) == 1 else ctx.inputs,
            "count": len(ctx.inputs),
        }


def _extract_confidence(value: Any) -> float | None:
    if isinstance(value, dict):
        conf = value.get("confidence")
        if isinstance(conf, (int, float)):
            return float(conf)
        if isinstance(value.get("selected"), dict):
            return _extract_confidence(value["selected"])
    return None


def render_template(value: Any, ctx: ExecutionContext) -> Any:
    """Resolve {{input}}, {{variables.name}} and {{nodes.<id>}} placeholders."""
    if not isinstance(value, str):
        return value
    out = value
    out = out.replace("{{input}}", json.dumps(ctx.variables.get("input"), ensure_ascii=False, default=str))
    for name, val in ctx.variables.items():
        out = out.replace("{{variables." + name + "}}",
                          json.dumps(val, ensure_ascii=False, default=str))
    for node_id, val in ctx.outputs.items():
        out = out.replace("{{nodes." + node_id + "}}",
                          json.dumps(val, ensure_ascii=False, default=str))
    return out


_REGISTRY: dict[str, NodeExecutor] = {
    "input": InputExecutor(),
    "jev_decision": JevDecisionExecutor(),
    "llm": LLMExecutor(),
    "python": PythonExecutor(),
    "http_request": HttpRequestExecutor(),
    "condition": ConditionExecutor(),
    "output": OutputExecutor(),
}


def registry() -> dict[str, NodeExecutor]:
    return _REGISTRY
