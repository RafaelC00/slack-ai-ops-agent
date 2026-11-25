# Design — Slack AI Ops Agent (marketing-ops assistant)

Status: approved spec, Python scaffold stage. Rafael approved 2026-11-25.

## Intent / why
A portfolio piece that proves Forward-Deployed / Applied-AI skill with a single
link: a production **RAG agent with evals**, reachable from **Slack**. Doubles as
the proof URL on in-flight applications. Shaped by a dated market scan of 8
currently-open LATAM-remote AI-engineer roles (2026-11-25): the recurring
requirements are agentic AI in production, LLM systems, **Python**, agent
frameworks, **RAG**, and **evals as the differentiator** — so the repo leads with
those. Slack is kept as the interface (and the thing Rafael enjoys building).

## What it is
A marketing-ops assistant. It answers from a knowledge base (campaign briefs,
pixel/tracking specs, A/B-test results) and takes a few real actions, talked to
in a Slack thread.

## Goals
- Retrieval-grounded answers (RAG), never hallucinated.
- The agent *acts*: 2–3 typed tools, not chat-only.
- Every run traced and logged (observability — what FDE interviews probe).
- A hand-built eval suite with published pass-rate numbers in the README.
- Deployed and live; model provider swappable for the eval comparison.

## Non-goals
Not a general chatbot. Not multi-tenant SaaS. No billing. No fine-tuning (a later
portfolio repo).

## Anti-goals (failure even if it "works")
- A demo with no eval numbers in the README.
- A bot that can't say "I don't know" when retrieval misses.

## Approaches considered
1. **Python (FastAPI) + Slack, chosen.** Matches 7/8 verified roles that require
   Python; FastAPI is light to host; a hand-built eval harness reads as "I built
   an evaluation suite," which is the differentiator in the strongest roles.
2. TypeScript/Node on Vercel (first draft). Matches only the 2 roles that accept
   "Python or TypeScript"; reframes evals as a wired tool rather than built.
   Rejected after the market scan.
3. No-Slack pure CLI/API agent. Leanest match but drops the Slack interface
   Rafael wants. Rejected.

## Architecture (chosen)
```
Slack → FastAPI  POST /slack/events
          • verify signature, ack < 3s, run agent in background
          • agent loop (model via provider router)
                ├─ kb_search         → pgvector over campaign docs
                ├─ experiment_lookup → A/B result by name/id
                └─ create_followup   → write a task
          • post reply in thread
Every step → Postgres (runs) → /dashboard (read-only traces)
Evals: evals/run.py over golden.yaml → correctness + grounded + refusal rates
```

## Decided
- Language: Python 3.11 / FastAPI. Host: Vercel (ASGI) or any container.
- DB/vectors: Neon Postgres + pgvector.
- Model: provider-routed (Anthropic/OpenRouter/Ollama) via one adapter.
- Evals: hand-built harness (`evals/run.py`), runnable offline with `--mock`.

## Left to the builder
- Tool schemas' final shape and the seed knowledge-base content (`data/`).
- Retrieval params (chunk size, top-k) — tune against the golden set.
- Dashboard styling.
- Wire the openrouter/ollama model branches and the DB layer in `app/rag/store.py`.

## Secrets / accounts needed from Rafael — see SETUP.md
Nothing goes live until those exist. No secret is committed; `.env.example` only.
