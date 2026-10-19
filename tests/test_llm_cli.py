"""The CLI provider's protocol: rendering the conversation and parsing replies (no model call)."""

import json

from agentkit.llm_cli import _parse_reply, _render_conversation


def test_parses_tool_calls_even_inside_a_code_fence():
    text = '```json\n{"tool_calls": [{"name": "run_sql", "arguments": {"query": "SELECT 1"}}]}\n```'
    assert _parse_reply(text)["tool_calls"][0]["arguments"] == {"query": "SELECT 1"}


def test_plain_text_is_taken_as_the_final_answer():
    assert _parse_reply("There are 6 lines.") == {"content": "There are 6 lines."}


def test_conversation_keeps_requests_and_results_in_order():
    call = {"id": "call_1", "type": "function", "function": {"name": "run_sql", "arguments": '{"query": "SELECT 1"}'}}
    text = _render_conversation([
        {"role": "user", "content": "How many?"},
        {"role": "assistant", "content": None, "tool_calls": [call]},
        {"role": "tool", "tool_call_id": "call_1", "content": json.dumps({"rows": [[6]]})},
    ])
    assert text.index("USER:") < text.index("YOU REQUESTED:") < text.index("RESULT (call_1)")
    assert text.endswith("Reply now with one JSON object.")
