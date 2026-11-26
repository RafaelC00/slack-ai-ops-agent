"""Route tests for /slack/events (offline; signature + _handle are stubbed)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app import main


def _client(monkeypatch, handled: list):
    monkeypatch.setattr(main, "is_valid_slack_request", lambda **_: True)

    async def fake_handle(event):
        handled.append(event)

    monkeypatch.setattr(main, "_handle", fake_handle)
    return TestClient(main.app)


def test_url_verification_echoes_challenge(monkeypatch):
    client = _client(monkeypatch, [])
    body = json.dumps({"type": "url_verification", "challenge": "abc123"})
    r = client.post("/slack/events", content=body)
    assert r.status_code == 200
    assert r.text == "abc123"


def test_app_mention_is_handled(monkeypatch):
    handled: list = []
    client = _client(monkeypatch, handled)
    body = json.dumps(
        {"type": "event_callback", "event": {"type": "app_mention", "text": "hi", "channel": "C1"}}
    )
    r = client.post("/slack/events", content=body)
    assert r.status_code == 200
    assert len(handled) == 1 and handled[0]["channel"] == "C1"


def test_retry_is_ignored(monkeypatch):
    handled: list = []
    client = _client(monkeypatch, handled)
    body = json.dumps(
        {"type": "event_callback", "event": {"type": "app_mention", "text": "hi", "channel": "C1"}}
    )
    r = client.post("/slack/events", content=body, headers={"X-Slack-Retry-Num": "1"})
    assert r.status_code == 200
    assert handled == []  # retry must not reprocess


def test_bot_message_is_ignored(monkeypatch):
    handled: list = []
    client = _client(monkeypatch, handled)
    body = json.dumps(
        {"type": "event_callback", "event": {"type": "message", "bot_id": "B1", "text": "x"}}
    )
    r = client.post("/slack/events", content=body)
    assert r.status_code == 200
    assert handled == []


def test_bad_signature_401(monkeypatch):
    monkeypatch.setattr(main, "is_valid_slack_request", lambda **_: False)
    client = TestClient(main.app)
    r = client.post("/slack/events", content="{}")
    assert r.status_code == 401
