"""Provider-routed model call.

One interface, swappable backend. Returns either
  {"tool_call": {"name", "input"}}  or  {"answer": str}.

Providers:
- ollama    : local, keyless. A raw open model (e.g. qwen3.5:4b) with NO native
              tool API — we drive tool-use with a JSON protocol (format=json).
              This is the "agentic on a raw model" path.
- anthropic : native tool-use (sketch; needs ANTHROPIC_API_KEY).
- replicate : TODO (blocked until the Replicate account has billing).
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from app.agent.tools import Tool


def _provider() -> str:
    return os.getenv("MODEL_PROVIDER", "ollama")


async def call_model(messages: list[dict], tools: list[Tool]) -> dict[str, Any]:
    p = _provider()
    if p == "ollama":
        return await _ollama(messages, tools)
    if p == "openrouter":
        return await _openrouter(messages, tools)
    if p == "anthropic":
        return await _anthropic(messages, tools)
    raise NotImplementedError(f"provider {p!r} not wired (replicate blocked on billing)")


# --- ollama (JSON tool protocol) --------------------------------------------
def _protocol(tools: list[Tool]) -> str:
    lines = [
        "Respond with a SINGLE JSON object and nothing else.",
        'To use a tool:  {\"tool\": \"<name>\", \"input\": { ... }}',
        'To answer:      {\"answer\": \"<text>\"}',
        "Available tools:",
    ]
    for t in tools:
        props = ", ".join((t.parameters.get("properties") or {}).keys())
        lines.append(f'- {t.name}({props}): {t.description}')
    return "\n".join(lines)


async def _ollama(messages: list[dict], tools: list[Tool]) -> dict[str, Any]:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("MODEL_NAME", "qwen3.5:4b")

    sys_core = next((m["content"] for m in messages if m["role"] == "system"), "")
    om = [{"role": "system", "content": sys_core + "\n\n" + _protocol(tools)}]
    for m in messages:
        if m["role"] == "system":
            continue
        if m["role"] == "tool":
            om.append({"role": "user", "content": f'Observation from {m.get("name")}: {m["content"]}'})
        else:
            om.append({"role": m["role"], "content": m["content"]})

    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{base}/api/chat",
            json={"model": model, "messages": om, "stream": False,
                  "format": "json", "keep_alive": "10m",
                  "options": {"temperature": 0, "num_predict": 512}},
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
    return _parse(content)


def _parse(content: str) -> dict[str, Any]:
    try:
        obj = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {"answer": (content or "").strip()}
    if not isinstance(obj, dict):
        return {"answer": str(obj)}

    # tool call in a few shapes the model might emit
    name = obj.get("tool") or obj.get("action")
    tc = obj.get("tool_call")
    if isinstance(tc, dict):
        return {"tool_call": {"name": tc.get("name"), "input": tc.get("input") or tc.get("arguments") or {}}}
    if name and str(name).lower() not in ("none", "answer") and "answer" not in obj:
        inp = obj.get("input") or obj.get("arguments") or obj.get("parameters") or {}
        return {"tool_call": {"name": str(name), "input": inp if isinstance(inp, dict) else {}}}

    ans = obj.get("answer") or obj.get("final") or obj.get("response") or obj.get("text")
    return {"answer": str(ans) if ans is not None else json.dumps(obj)}


# --- openrouter (OpenAI-compatible; same JSON tool protocol) -----------------
async def _openrouter(messages: list[dict], tools: list[Tool]) -> dict[str, Any]:
    key = os.environ["OPENROUTER_API_KEY"]
    model = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")

    sys_core = next((m["content"] for m in messages if m["role"] == "system"), "")
    om = [{"role": "system", "content": sys_core + "\n\n" + _protocol(tools)}]
    for m in messages:
        if m["role"] == "system":
            continue
        if m["role"] == "tool":
            om.append({"role": "user", "content": f'Observation from {m.get("name")}: {m["content"]}'})
        else:
            om.append({"role": m["role"], "content": m["content"]})

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/RafaelC00/slack-ai-ops-agent",
                "X-Title": "slack-ai-ops-agent",
            },
            json={"model": model, "messages": om, "temperature": 0,
                  "response_format": {"type": "json_object"}},
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    return _parse(content)


# --- anthropic (native tools; needs a key) ----------------------------------
async def _anthropic(messages: list[dict], tools: list[Tool]) -> dict[str, Any]:
    specs = [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools]
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    turns = [{"role": m["role"], "content": m["content"]} for m in messages
             if m["role"] in ("user", "assistant")]
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                     "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": os.getenv("MODEL_NAME", "claude-sonnet-4-5"), "max_tokens": 1024,
                  "system": system, "tools": specs, "messages": turns},
        )
        resp.raise_for_status()
        data = resp.json()
    for block in data.get("content", []):
        if block.get("type") == "tool_use":
            return {"tool_call": {"name": block["name"], "input": block.get("input", {})}}
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return {"answer": text}
