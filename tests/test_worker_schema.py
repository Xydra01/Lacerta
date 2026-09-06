from __future__ import annotations

from lacerta.core.schema import (
    _prepare_ollama_schema,
    build_worker_json_schema,
    parse_tool_turn,
)


def test_prepare_ollama_schema_inlines_and_strips() -> None:
    schema = {
        "type": "object",
        "$defs": {"Arg": {"type": "object", "properties": {"x": {"type": "string"}}}},
        "properties": {
            "reasoning": {"type": "string", "description": "why"},
            "tools": {
                "type": "array",
                "items": {"$ref": "#/$defs/Arg"},
            },
        },
    }
    out = _prepare_ollama_schema(schema, simplify=True)
    assert "$defs" not in out
    assert "description" not in out.get("properties", {}).get("reasoning", {})
    assert out.get("additionalProperties") is False
    tools_items = out["properties"]["tools"]["items"]
    assert "$ref" not in tools_items
    assert tools_items.get("additionalProperties") is False


def test_build_worker_json_schema_enum() -> None:
    names = frozenset({"read_file", "write_file"})
    schema = build_worker_json_schema(names)
    enum = schema["properties"]["tools"]["items"]["properties"]["name"]["enum"]
    assert set(enum) == names
    assert schema["properties"]["tools"]["maxItems"] == 1
    assert set(schema["required"]) == {"reasoning", "tools", "final_report"}


def test_parse_tool_turn_happy() -> None:
    raw = (
        '{"reasoning":"write","tools":[{"name":"write_file",'
        '"arguments":{"path":"a.py","content":"x"}}],"final_report":""}'
    )
    parsed = parse_tool_turn(raw, frozenset({"write_file"}))
    assert parsed is not None
    assert parsed["tools"][0]["name"] == "write_file"


def test_parse_tool_turn_final_report() -> None:
    raw = '{"reasoning":"done","tools":[],"final_report":"ok"}'
    parsed = parse_tool_turn(raw, frozenset({"write_file"}))
    assert parsed is not None
    assert parsed["final_report"] == "ok"


def test_parse_tool_turn_invalid() -> None:
    assert parse_tool_turn("not json", frozenset({"write_file"})) is None
    assert parse_tool_turn('{"tools":[]}', frozenset({"write_file"})) is None
    bad = (
        '{"reasoning":"x","tools":[{"name":"run_command","arguments":{}}],'
        '"final_report":""}'
    )
    assert parse_tool_turn(bad, frozenset({"write_file"})) is None
