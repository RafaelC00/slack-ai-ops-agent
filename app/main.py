"""FastAPI entrypoint. Slack posts events here.

We verify the signature, answer the url_verification handshake, and for real
events run the agent and post the reply before returning.

Why synchronous (not a BackgroundTask): on serverless (Vercel) the function is
frozen once it returns, so post-response background work isn't reliably executed.
Processing inline can exceed Slack's 3s window, so Slack will retry — we ignore
retries (X-Slack-Retry-Num) to avoid duplicate replies, and the first delivery
does the work.
"""

from __future__ import annotations

import json
import os

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse

from app.agent.loop import run_agent
from app.agent.model import call_model
from app.config import load_env
from app.dashboard import render_dashboard
from app.rag.store import recent_steps, record_step
from app.slack.post import post_reply
from app.slack.verify import is_valid_slack_request

# Load .env for local dev. Uses setdefault, so platform-provided env vars
# (Vercel) always win and this is a no-op in production.
load_env()

app = FastAPI(title="slack-ai-ops-agent")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    """Read-only trace viewer. Never raises: a DB problem renders an empty state."""
    try:
        steps = await recent_steps(limit=100)
        return HTMLResponse(render_dashboard(steps, db_ok=True))
    except Exception:  # noqa: BLE001 - a dashboard DB hiccup must render, not 500
        return HTMLResponse(render_dashboard([], db_ok=False), status_code=200)


@app.post("/slack/events")
async def slack_events(request: Request) -> Response:
    raw = await request.body()

    if not is_valid_slack_request(
        signing_secret=os.environ["SLACK_SIGNING_SECRET"],
        timestamp=request.headers.get("x-slack-request-timestamp", ""),
        signature=request.headers.get("x-slack-signature", ""),
        raw_body=raw,
    ):
        return Response(status_code=401)

    payload = json.loads(raw or b"{}")

    # Slack's one-time endpoint handshake.
    if payload.get("type") == "url_verification":
        return Response(content=payload["challenge"], media_type="text/plain")

    # We process inline (see module docstring), which can exceed Slack's 3s window,
    # so Slack retries. Ignore retries so the reply isn't posted more than once.
    if request.headers.get("x-slack-retry-num"):
        return Response(status_code=200)

    event = payload.get("event", {})
    if event.get("type") in ("app_mention", "message") and not event.get("bot_id"):
        await _handle(event)

    return Response(status_code=200)


async def _handle(event: dict) -> None:
    text = event.get("text", "")
    channel = event.get("channel")
    thread_ts = event.get("thread_ts") or event.get("ts")

    result = await run_agent(text, call_model=call_model, record=record_step)

    await post_reply(channel=channel, thread_ts=thread_ts, text=result.answer)
