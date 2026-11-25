# Slack AI Ops Agent

A production **RAG agent with evals**, reachable from **Slack**. Ask it about
campaigns, tracking/pixel specs, or A/B-test results in a thread; it answers from
a knowledge base, takes real actions, traces every step, and is graded by an eval
suite whose numbers are published below.

> Built to show applied-AI / forward-deployed engineering end to end:
> retrieval → tool-use → observability → **evaluation** → deployment.

---

## Why this exists
Most "AI assistant" demos are a prompt and a prayer. This one is built the way a
team would actually trust it: answers are grounded in a knowledge base, the agent
acts through typed tools, every step is logged, and a hand-built eval suite
reports — in real numbers — how often it's correct, stays grounded, and correctly
says "I don't know."

## Architecture
```
Slack  ──▶  FastAPI  POST /slack/events
             • verify signature, ack < 3s, run agent in background
             • agent loop (model via provider router)
                 ├─ kb_search         → pgvector over campaign docs
                 ├─ experiment_lookup → A/B result by name/id
                 └─ create_followup   → write a task
             • reply in thread
Every step ──▶ Postgres (runs)  ──▶  /dashboard (read-only traces)
Evals: evals/run.py over golden.yaml ──▶ correctness · grounded · refusal
```
Design rationale (and the market scan that shaped it) in [DESIGN.md](./DESIGN.md).

## Stack
Python 3.11 · FastAPI · Slack · Neon Postgres + pgvector · local keyless
embeddings (fastembed / bge-small) · provider-routed model — **OpenRouter**
(`gpt-4o-mini`) hosted, **Ollama** (`qwen3.5:4b`) local, via one JSON tool
protocol so even a model with no native tool API does agentic tool-use ·
hand-built eval harness.

## Eval results
Live run — `openai/gpt-4o-mini` via OpenRouter, against the real Neon KB (`python evals/run.py`):

| Metric | Set | Result |
|---|---|---|
| Correctness (in-KB) | golden-v1 (n=3) | **3/3** |
| Groundedness (answer backed by a tool observation) | golden-v1 | **3/3** |
| Refusal (out-of-KB → "I don't know") | golden-v1 (n=2) | **2/2** |
| **Total** | golden-v1 (n=5) | **5/5 (100%)** |

The harness earns its keep: an earlier run caught the model answering a spec
question from its own priors *without* grounding — a real reliability bug that a
tightened grounding rule fixed. It also runs fully offline for CI:
`python evals/run.py --mock` exercises the whole scoring path with a canned model —
no keys or DB needed.

## Run
```bash
python -m venv .venv && . .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install -e ".[dev]"
cp .env.example .env            # fill values — see SETUP.md
python evals/run.py --mock      # eval harness, no keys needed
uvicorn app.main:app --reload   # the service (needs Slack + DB + model to be live)
```
See [SETUP.md](./SETUP.md) for the accounts/secrets a live deploy needs.

## Status
Working end to end locally: retrieval, structured lookup, the agent loop, tracing,
and the eval suite all run against **live Neon + OpenRouter** (5/5 above). Remaining
for a hosted demo: finish the Slack reply wiring in `app/main.py` (verify + ack are
done; the `chat.postMessage` reply is the last TODO) and deploy to Vercel. Replicate
is kept as a provider branch, deferred until that account has billing.
