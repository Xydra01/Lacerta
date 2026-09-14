"""Ollama JSON schema helpers and worker action parsing."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any


def _inline_defs(schema: dict[str, Any]) -> dict[str, Any]:
    """Expand $ref / $defs into a flat schema for weak local models."""
    defs = dict(schema.get("$defs") or schema.get("definitions") or {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                ref = str(node["$ref"])
                name = ref.rsplit("/", 1)[-1]
                if name in defs:
                    return resolve(deepcopy(defs[name]))
                return node
            return {k: resolve(v) for k, v in node.items() if k not in ("$defs", "definitions")}
        if isinstance(node, list):
            return [resolve(x) for x in node]
        return node

    out = resolve(schema)
    if isinstance(out, dict):
        out.pop("$defs", None)
        out.pop("definitions", None)
    return out if isinstance(out, dict) else {"type": "object"}


def _enforce_additional_properties_false(schema: dict[str, Any]) -> dict[str, Any]:
    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            out = {k: walk(v) for k, v in node.items()}
            if out.get("type") == "object" or "properties" in out:
                out.setdefault("additionalProperties", False)
            return out
        if isinstance(node, list):
            return [walk(x) for x in node]
        return node

    return walk(schema)


def _strip_descriptions(schema: dict[str, Any]) -> dict[str, Any]:
    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            return {
                k: walk(v)
                for k, v in node.items()
                if k not in ("description", "title")
            }
        if isinstance(node, list):
            return [walk(x) for x in node]
        return node

    return walk(schema)


def _prepare_ollama_schema(schema: dict[str, Any], *, simplify: bool) -> dict[str, Any]:
    out = _inline_defs(schema)
    out = _enforce_additional_properties_false(out)
    if simplify:
        out = _strip_descriptions(out)
    if out.get("type") != "object":
        out = {"type": "object", **out}
    return out


def build_agent_action_json_schema(
    tool_names: frozenset[str] | list[str],
    registry: dict[str, dict[str, Any]] | None = None,
    *,
    simplify: bool = True,
    max_tools_per_turn: int = 1,
    require_final_report: bool = False,
) -> dict[str, Any]:
    del registry, require_final_report  # flat schema; descriptions stripped when simplify
    names = sorted(tool_names)
    if not names:
        names = ["noop"]
    # Flat argument bag — avoids anyOf per-tool schemas that weak models mishandle.
    arg_props = {
        "path": {"type": "string"},
        "content": {"type": "string"},
        "old_string": {"type": "string"},
        "new_string": {"type": "string"},
        "pattern": {"type": "string"},
        "start_line": {"type": "integer"},
        "end_line": {"type": "integer"},
        "command": {"type": "string"},
        "max_matches": {"type": "integer"},
        "max_results": {"type": "integer"},
    }
    schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "reasoning": {"type": "string"},
            "tools": {
                "type": "array",
                "maxItems": max_tools_per_turn,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {"type": "string", "enum": names},
                        "arguments": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": arg_props,
                        },
                    },
                    "required": ["name", "arguments"],
                },
            },
            "final_report": {"type": "string"},
        },
        "required": ["reasoning", "tools", "final_report"],
    }
    return _prepare_ollama_schema(schema, simplify=simplify)


def build_worker_json_schema(tool_names: frozenset[str]) -> dict[str, Any]:
    from lacerta.workers.code_tools import CODE_TOOL_REGISTRY

    registry = {k: CODE_TOOL_REGISTRY[k] for k in tool_names if k in CODE_TOOL_REGISTRY}
    return build_agent_action_json_schema(
        tool_names,
        registry,
        simplify=True,
        max_tools_per_turn=1,
        require_final_report=False,
    )


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_json_object(text: str) -> str | None:
    """Return the first balanced {...} substring, or None.

    Small local models sometimes wrap valid JSON in a short preface/epilogue.
    Prefer the first object that looks like a Lacerta tool turn.
    """
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _loads_tool_json(text: str) -> dict[str, Any] | None:
    candidates: list[str] = [text]
    extracted = _extract_json_object(text)
    if extracted and extracted not in candidates:
        candidates.append(extracted)
    for cand in candidates:
        try:
            parsed = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def parse_tool_turn(raw: str, tools_allowed: frozenset[str]) -> dict[str, Any] | None:
    text = _strip_markdown_fence(raw or "")
    if not text:
        return None
    parsed = _loads_tool_json(text)
    if parsed is None:
        return None
    if "reasoning" not in parsed:
        # Tolerate missing reasoning from weaker models; keep schema cohesion.
        parsed["reasoning"] = ""
    tools = parsed.get("tools")
    if tools is None:
        parsed["tools"] = []
        tools = parsed["tools"]
    if not isinstance(tools, list):
        return None
    if len(tools) > 1:
        return None
    if "final_report" not in parsed:
        parsed["final_report"] = ""
    if tools:
        call = tools[0]
        # Tolerate models that emit a bare tool name string.
        if isinstance(call, str):
            call = {"name": call.strip(), "arguments": {}}
            tools[0] = call
            parsed["tools"] = tools
        if not isinstance(call, dict):
            return None
        name = str(call.get("name") or "").strip()
        if name and name not in tools_allowed:
            return None
        args = call.get("arguments")
        if args is None:
            call["arguments"] = {}
        elif not isinstance(args, dict):
            return None
        # Tolerate alternate key names some 3–4B models invent.
        if "path" not in call["arguments"] and "file" in call["arguments"]:
            call["arguments"]["path"] = call["arguments"].pop("file")
        if "content" not in call["arguments"] and "text" in call["arguments"]:
            call["arguments"]["content"] = call["arguments"].pop("text")
    return parsed
