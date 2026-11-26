"""Offline tests for the trace dashboard renderer (no DB, no network)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.dashboard import render_dashboard

SAMPLE = [
    {
        "kind": "tool",
        "tool": "kb_search",
        "input": {"query": "Q3 revenue Brazil"},
        "output": "NO_RESULTS",
        "at": datetime(2026, 11, 25, 23, 38, 25, tzinfo=UTC),
    },
    {
        "kind": "answer",
        "tool": None,
        "input": None,
        "output": "I don't have that in the knowledge base.",
        "at": datetime(2026, 11, 25, 23, 38, 29, tzinfo=UTC),
    },
]


def test_renders_rows_and_stats():
    html = render_dashboard(SAMPLE, db_ok=True)
    assert "kb_search" in html
    assert "Q3 revenue Brazil" in html
    assert ">1</div><div class=\"k\">tool calls" in html
    assert ">1</div><div class=\"k\">answers" in html
    assert "2026-11-25 23:38:29Z" in html  # last activity = newest row


def test_escapes_html_in_values():
    rows = [
        {
            "kind": "tool",
            "tool": "kb_search",
            "input": {"query": "<script>alert(1)</script>"},
            "output": "ok",
            "at": datetime(2026, 11, 25, tzinfo=UTC),
        }
    ]
    html = render_dashboard(rows, db_ok=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_empty_state():
    assert "No traces yet" in render_dashboard([], db_ok=True)


def test_db_down_state():
    assert "Could not reach the database" in render_dashboard([], db_ok=False)
