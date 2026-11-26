"""The agent loop should recover when the model calls kb_search with no query."""

from __future__ import annotations

import asyncio

from app.agent import loop as loop_mod
from app.agent.loop import run_agent
from app.agent.tools import Tool


def _run(user_text, model_outputs, tools):
    outs = iter(model_outputs)

    async def call_model(messages, _tools):
        return next(outs)

    async def record(_step):
        return None

    return asyncio.run(run_agent(user_text, call_model=call_model, record=record)), tools


def test_empty_kb_search_falls_back_to_user_question(monkeypatch):
    seen = {}

    async def fake_run(args):
        seen["args"] = args
        return "[spec-checkout-pixel] purchase fires on order completion"

    fake_kb = Tool(name="kb_search", description="", parameters={}, run=fake_run)
    monkeypatch.setattr(loop_mod, "TOOLS", [fake_kb])

    outputs = [
        {"tool_call": {"name": "kb_search", "input": {}}},  # model forgot the query
        {"answer": "Purchase fires on order completion [spec-checkout-pixel]."},
    ]
    res, _ = _run("what does the checkout pixel say about purchase?", outputs, [fake_kb])

    # the empty {} was replaced with the user's question
    assert seen["args"].get("query") == "what does the checkout pixel say about purchase?"
    assert res.grounded is True
    assert "order completion" in res.answer


def test_kb_search_keeps_explicit_query(monkeypatch):
    seen = {}

    async def fake_run(args):
        seen["args"] = args
        return "[doc] ok"

    fake_kb = Tool(name="kb_search", description="", parameters={}, run=fake_run)
    monkeypatch.setattr(loop_mod, "TOOLS", [fake_kb])

    outputs = [
        {"tool_call": {"name": "kb_search", "input": {"query": "Q3 revenue"}}},
        {"answer": "done"},
    ]
    _run("unrelated user text", outputs, [fake_kb])
    assert seen["args"]["query"] == "Q3 revenue"  # explicit query untouched
