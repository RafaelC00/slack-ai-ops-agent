"""The agent loop.

The model proposes a tool call; we run it, feed the observation back, repeat
until it answers. Every step is recorded so /dashboard can show exactly what the
agent did — the observability that makes it trustworthy and demo-able.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from app.agent.tools import TOOLS, Tool

MAX_STEPS = 6

SYSTEM = """You are a marketing-ops assistant in Slack.
Rules:
- For a specific A/B test's result — winner, lift, or significance — call experiment_lookup
  with the test name. Do this for any question about which variant won.
- NEVER state a fact about a campaign, pixel, tracking spec, or metric unless a tool you
  called in THIS conversation returned it. For these, call kb_search first and answer only
  from what it returns. If you have not called such a tool, you do not know.
- Don't repeat the same tool call with the same input. If kb_search returns NO_RESULTS and
  no other tool fits, say you don't know.
- Cite the source id (e.g. [spec-checkout-pixel]) of any fact you use.
- Only call create_followup after the user confirms."""


@dataclass
class Step:
    kind: str  # "tool" | "answer"
    at: str
    tool: str | None = None
    input: Any = None
    output: str | None = None


@dataclass
class RunResult:
    answer: str
    steps: list[Step] = field(default_factory=list)
    grounded: bool = False  # did the answer rest on a kb_search observation?


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_agent(
    user_text: str,
    *,
    call_model: Callable[[list[dict], list[Tool]], Awaitable[dict]],
    record: Callable[[Step], Awaitable[None]],
) -> RunResult:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_text},
    ]
    result = RunResult(answer="")
    by_name = {t.name: t for t in TOOLS}

    for _ in range(MAX_STEPS):
        out = await call_model(messages, TOOLS)

        if out.get("answer") is not None:
            step = Step(kind="answer", at=_now(), output=out["answer"])
            result.steps.append(step)
            await record(step)
            result.answer = out["answer"]
            return result

        call = out.get("tool_call")
        tool = by_name.get(call["name"]) if call else None
        if not tool:
            break

        observation = await tool.run(call.get("input", {}))
        # Both retrieval tools count as grounding when they return real data.
        if tool.name in ("kb_search", "experiment_lookup") and observation not in ("NO_RESULTS",):
            if not observation.startswith("ERROR"):
                result.grounded = True

        step = Step(
            kind="tool", at=_now(), tool=tool.name, input=call.get("input"), output=observation
        )
        result.steps.append(step)
        await record(step)
        messages.append({"role": "tool", "name": tool.name, "content": observation})

    result.answer = "I couldn't answer that reliably — a human should take a look."
    return result
