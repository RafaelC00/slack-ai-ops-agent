"""Read-only observability page for the agent's run traces.

Renders the recent rows of the `runs` table as a single self-contained HTML
page (no external assets, works in light and dark). This is the "we measure our
agents" surface: every tool call and answer the agent produced, newest first.
"""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from typing import Any

_MAX_CELL = 240  # chars before a cell is clipped (full text in the title tooltip)


def _fmt_when(at: Any) -> str:
    if isinstance(at, datetime):
        dt = at.astimezone(UTC) if at.tzinfo else at.replace(tzinfo=UTC)
        return dt.strftime("%Y-%m-%d %H:%M:%S") + "Z"
    return html.escape(str(at or ""))


def _fmt_value(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def _cell(v: Any) -> str:
    text = _fmt_value(v)
    full = html.escape(text, quote=True)
    shown = html.escape(text[:_MAX_CELL])
    clip = "…" if len(text) > _MAX_CELL else ""
    return f'<span title="{full}">{shown}{clip}</span>'


def render_dashboard(steps: list[dict], *, db_ok: bool = True) -> str:
    tool_calls = sum(1 for s in steps if s.get("kind") == "tool")
    answers = sum(1 for s in steps if s.get("kind") == "answer")
    last = _fmt_when(steps[0]["at"]) if steps else "—"

    rows = []
    for s in steps:
        kind = s.get("kind") or ""
        is_tool = kind == "tool"
        badge_cls = "tool" if is_tool else "answer"
        label = html.escape(s.get("tool") or ("answer" if kind == "answer" else kind or "—"))
        rows.append(
            "<tr>"
            f'<td class="when">{_fmt_when(s.get("at"))}</td>'
            f'<td><span class="badge {badge_cls}">{html.escape(kind or "")}</span></td>'
            f'<td class="tool">{label}</td>'
            f'<td class="mono">{_cell(s.get("input"))}</td>'
            f'<td class="mono">{_cell(s.get("output"))}</td>'
            "</tr>"
        )

    if not steps:
        note = (
            "No traces yet. Mention the bot in Slack (or run the agent) and every "
            "step will appear here."
            if db_ok
            else "Could not reach the database. Traces are unavailable right now."
        )
        body = f'<div class="empty">{html.escape(note)}</div>'
    else:
        body = (
            '<div class="tablewrap"><table>'
            "<thead><tr>"
            "<th>Time (UTC)</th><th>Kind</th><th>Tool</th><th>Input</th><th>Output</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table></div>"
        )

    return _PAGE.format(
        total=len(steps), tool_calls=tool_calls, answers=answers, last=html.escape(last), body=body
    )


_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Run Traces</title>
<style>
  :root {{
    --bg:#f7f7f8; --surface:#ffffff; --ink:#1a1a1f; --muted:#6b6b76;
    --line:#e6e6ea; --accent:#4a154b; --tool:#2563eb; --answer:#15803d;
    --chip-bg:#f0f0f3;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg:#0f0f12; --surface:#17171c; --ink:#ececf1; --muted:#9a9aa6;
      --line:#26262e; --accent:#c9a2cb; --tool:#60a5fa; --answer:#4ade80;
      --chip-bg:#22222a;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg:#0f0f12; --surface:#17171c; --ink:#ececf1; --muted:#9a9aa6;
    --line:#26262e; --accent:#c9a2cb; --tool:#60a5fa; --answer:#4ade80;
    --chip-bg:#22222a;
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; background:var(--bg); color:var(--ink);
    font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  }}
  .wrap {{ max-width:1100px; margin:0 auto; padding:32px 16px 64px; }}
  header h1 {{ margin:0; font-size:22px; letter-spacing:-0.01em; }}
  header p {{ margin:4px 0 0; color:var(--muted); font-size:14px; }}
  .stats {{ display:flex; flex-wrap:wrap; gap:12px; margin:22px 0; }}
  .stat {{
    background:var(--surface); border:1px solid var(--line); border-radius:10px;
    padding:12px 16px; min-width:120px;
  }}
  .stat .n {{ font-size:22px; font-weight:650; font-variant-numeric:tabular-nums; }}
  .stat .k {{ font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:0.04em; }}
  .tablewrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:12px; background:var(--surface); }}
  table {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
  th, td {{ text-align:left; padding:10px 14px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ font-size:11px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted); font-weight:600; }}
  tr:last-child td {{ border-bottom:0; }}
  td.when {{ color:var(--muted); white-space:nowrap; font-variant-numeric:tabular-nums; }}
  td.tool {{ font-weight:600; white-space:nowrap; }}
  td.mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12.5px;
    max-width:380px; overflow:hidden; text-overflow:ellipsis; }}
  td.mono span {{ display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px; font-weight:600;
    background:var(--chip-bg); }}
  .badge.tool {{ color:var(--tool); }}
  .badge.answer {{ color:var(--answer); }}
  .empty {{ background:var(--surface); border:1px solid var(--line); border-radius:12px;
    padding:40px; text-align:center; color:var(--muted); }}
  footer {{ margin-top:18px; color:var(--muted); font-size:12.5px; }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>AI Ops Agent &mdash; run traces</h1>
      <p>Read-only view of what the agent actually did: every tool call and answer, newest first.</p>
    </header>
    <div class="stats">
      <div class="stat"><div class="n">{total}</div><div class="k">steps shown</div></div>
      <div class="stat"><div class="n">{tool_calls}</div><div class="k">tool calls</div></div>
      <div class="stat"><div class="n">{answers}</div><div class="k">answers</div></div>
      <div class="stat"><div class="n">{last}</div><div class="k">last activity</div></div>
    </div>
    {body}
    <footer>Generated from the <code>runs</code> table. This is the observability surface the
    eval suite grades against.</footer>
  </div>
</body>
</html>"""
