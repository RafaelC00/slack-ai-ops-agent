"""Offline tests for the Slack reply path.

These never touch the network: they exercise the graceful short-circuits that
keep the eval/CI path alive when there's no bot token or channel, and confirm
that with a token present we call chat.postMessage with the right thread args.
"""

from __future__ import annotations

import asyncio

from app.slack import post


def test_no_token_is_noop(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    sent = asyncio.run(
        post.post_reply(channel="C123", thread_ts="1.1", text="hi")
    )
    assert sent is False


def test_token_but_no_channel_is_noop(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    sent = asyncio.run(
        post.post_reply(channel=None, thread_ts="1.1", text="hi")
    )
    assert sent is False


def test_posts_in_thread_when_configured(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    calls: list[dict] = []

    class FakeClient:
        def __init__(self, token: str):
            calls.append({"token": token})

        def chat_postMessage(self, **kwargs):
            calls.append(kwargs)
            return {"ok": True}

    monkeypatch.setattr(post, "WebClient", FakeClient)

    sent = asyncio.run(
        post.post_reply(channel="C123", thread_ts="1699999999.000100", text="done")
    )

    assert sent is True
    msg = calls[-1]
    assert msg["channel"] == "C123"
    assert msg["thread_ts"] == "1699999999.000100"
    assert msg["text"] == "done"
