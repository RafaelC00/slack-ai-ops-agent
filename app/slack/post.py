"""Post the agent's reply back into the Slack thread.

Uses slack_sdk's synchronous ``WebClient`` from a worker thread (the same
``asyncio.to_thread`` pattern as the trace writer in ``app/rag/store.py``), so
we stay off aiohttp and keep one HTTP style across the app.

If ``SLACK_BOT_TOKEN`` is unset (local dev, evals, CI) this is a logged no-op:
the agent still runs and traces every step, it just has no Slack workspace to
answer into. That keeps the offline eval path and the live Slack path on the
same code.
"""

from __future__ import annotations

import asyncio
import logging
import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

log = logging.getLogger("slack-ai-ops-agent")


async def post_reply(*, channel: str | None, thread_ts: str | None, text: str) -> bool:
    """Post ``text`` into ``channel`` as a threaded reply. Returns True on send.

    Never raises on a Slack/API problem — a failed post is logged and reported
    via the return value, so a background task can't crash the worker.
    """
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        log.info(
            "SLACK_BOT_TOKEN unset; skipping Slack post (channel=%s): %s",
            channel,
            text[:80],
        )
        return False
    if not channel:
        log.warning("no channel on event; cannot post reply")
        return False

    def _send() -> bool:
        client = WebClient(token=token)
        try:
            client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=text)
            return True
        except SlackApiError as exc:
            log.error("chat.postMessage failed: %s", exc.response.get("error"))
            return False

    return await asyncio.to_thread(_send)
