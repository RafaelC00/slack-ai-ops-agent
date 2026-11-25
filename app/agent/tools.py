"""Typed tools the agent can call.

Each tool has a JSON schema the model sees and an async `run`. Small, typed
tools are what let the agent *act* reliably instead of only chatting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.rag.store import experiment_by_name, search_kb, write_followup


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema shown to the model
    run: Callable[[dict[str, Any]], Awaitable[str]]


def _pick(args: dict[str, Any], *keys: str) -> str:
    """Small models are inconsistent with argument names. Accept the known keys,
    else fall back to the first string value in the args."""
    for k in keys:
        v = args.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return next((v for v in args.values() if isinstance(v, str) and v.strip()), "")


async def _kb_search(args: dict[str, Any]) -> str:
    query = _pick(args, "query", "q", "text", "search", "question")
    if not query:
        return "NO_RESULTS"
    hits = await search_kb(query, top_k=args.get("top_k", 5))
    if not hits:
        return "NO_RESULTS"
    # Return text + source id so the model can cite; groundedness depends on this.
    return "\n".join(f"[{h['source_id']}] {h['text']}" for h in hits)


async def _experiment_lookup(args: dict[str, Any]) -> str:
    row = await experiment_by_name(_pick(args, "name", "id", "experiment", "query"))
    return row or "NO_RESULTS"


async def _create_followup(args: dict[str, Any]) -> str:
    title = _pick(args, "title", "name", "summary")
    if not title:
        return "ERROR: a title is required"
    new_id = await write_followup(title, args.get("context", "") or "")
    return f"created followup {new_id}"


KB_SEARCH = Tool(
    name="kb_search",
    description=(
        "Search the marketing knowledge base (campaign briefs, pixel/tracking "
        "specs, A/B results). Call this before stating any fact."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
    run=_kb_search,
)

EXPERIMENT_LOOKUP = Tool(
    name="experiment_lookup",
    description="Look up one A/B test's result (winner, lift, significance).",
    parameters={
        "type": "object",
        "properties": {"name": {"type": "string"}, "id": {"type": "string"}},
    },
    run=_experiment_lookup,
)

CREATE_FOLLOWUP = Tool(
    name="create_followup",
    description="Create a follow-up task when a human is needed. Confirm with the user first.",
    parameters={
        "type": "object",
        "properties": {"title": {"type": "string"}, "context": {"type": "string"}},
        "required": ["title"],
    },
    run=_create_followup,
)

TOOLS: list[Tool] = [KB_SEARCH, EXPERIMENT_LOOKUP, CREATE_FOLLOWUP]
