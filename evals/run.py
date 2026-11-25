"""Hand-built eval harness.

Runs the agent over evals/golden.yaml and scores correctness, groundedness, and
refusal. Prints a table and the pass rates that go in the README. Built from
scratch (not a framework) because "I built an evaluation suite" is the point.

Usage:
  python evals/run.py            # uses the real agent (needs model + DB)
  python evals/run.py --mock     # uses a canned model, so the harness itself
                                  # is demonstrable with no keys or DB
"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.config import load_env  # noqa: E402

load_env()  # live mode needs DATABASE_URL + OPENROUTER_API_KEY from .env

from app.agent.loop import Step, run_agent  # noqa: E402

GOLDEN = pathlib.Path(__file__).with_name("golden.yaml")

REFUSAL_MARKERS = ("i don't know", "i do not know", "no data", "not sure", "can't find", "cannot find")


def looks_like_refusal(answer: str) -> bool:
    a = answer.lower()
    return any(m in a for m in REFUSAL_MARKERS)


def score(case: dict, answer: str, grounded: bool) -> tuple[bool, str]:
    if case.get("expect_refusal"):
        ok = looks_like_refusal(answer)
        return ok, "refused" if ok else "INVENTED an answer"
    if case.get("require_grounded") and not grounded:
        return False, "ungrounded (no kb_search hit)"
    if "expect_contains" in case:
        ok = case["expect_contains"].lower() in answer.lower()
        return ok, "correct" if ok else f"missing {case['expect_contains']!r}"
    return grounded, "grounded"


async def _noop_record(_: Step) -> None:
    return None


def install_mock_store() -> None:
    """Swap the DB-backed tool functions for in-memory fakes, so --mock runs the
    real loop + tools + scoring with no database."""
    import app.agent.tools as t

    async def fake_search_kb(query: str, top_k: int = 5):
        return [{
            "source_id": "brief-1",
            "text": "October homepage hero A/B test: Variant B won. The checkout pixel fires a purchase event. Q4 retention campaign objective: win-back lapsed buyers.",
        }]

    async def fake_experiment(name_or_id: str):
        return "Variant B won (+12% conversion, significant)"

    async def fake_followup(title: str, context: str = ""):
        return "fup-1"

    t.search_kb = fake_search_kb
    t.experiment_by_name = fake_experiment
    t.write_followup = fake_followup


def mock_model_factory():
    """A canned model so the harness runs offline. In-KB → cite; out-of-KB → refuse."""
    async def call_model(messages, tools):
        user = next((m["content"] for m in messages if m["role"] == "user"), "")
        used_tool = any(m.get("role") == "tool" for m in messages)
        if not used_tool and ("revenue" not in user.lower() and "team" not in user.lower()):
            return {"tool_call": {"name": "kb_search", "input": {"query": user}}}
        if "revenue" in user.lower() or "team" in user.lower():
            return {"answer": "I don't know — there's no data on that in the knowledge base."}
        return {"answer": "Variant B won; the checkout pixel fires a purchase event. [brief-1]"}
    return call_model


async def main(mock: bool) -> int:
    cases = yaml.safe_load(GOLDEN.read_text())["cases"]
    if mock:
        install_mock_store()
        call_model = mock_model_factory()
    else:
        from app.agent.model import call_model  # real provider

    passed = 0
    print(f"{'id':<22} {'result':<10} note")
    print("-" * 60)
    for case in cases:
        res = await run_agent(case["question"], call_model=call_model, record=_noop_record)
        ok, note = score(case, res.answer, res.grounded)
        passed += ok
        print(f"{case['id']:<22} {'PASS' if ok else 'FAIL':<10} {note}")

    rate = passed / len(cases) * 100
    print("-" * 60)
    print(f"{passed}/{len(cases)} passed  ({rate:.0f}%)")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()
    raise SystemExit(asyncio.run(main(args.mock)))
