"""Data layer: pgvector retrieval, experiment lookups, follow-ups, run tracing.

Postgres-backed (Neon + pgvector). The public functions are async (the agent
loop awaits them); the actual DB + embedding work is sync and runs in a worker
thread so it never blocks the event loop.

Schema (created by init_schema / scripts/seed_kb.py):
  kb_chunks(id, source_id, text, embedding vector(384))
  experiments(id, name, winner, lift_pct, significant, summary)
  followups(id, title, context, created_at)
  runs(id, step_kind, tool, input jsonb, output, at)
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import TYPE_CHECKING

import psycopg
from pgvector.psycopg import register_vector

from app.rag.embed import EMBED_DIM, embed_one

if TYPE_CHECKING:
    from app.agent.loop import Step


def _connect() -> psycopg.Connection:
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    register_vector(conn)
    return conn


def vec_literal(vec: list[float]) -> str:
    """pgvector text literal, e.g. '[0.1,0.2,...]'. Used with an explicit
    `%s::vector` cast so the parameter is unambiguously a vector, not float8[]."""
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def init_schema() -> None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("create extension if not exists vector")
        cur.execute(
            f"""create table if not exists kb_chunks(
                id bigserial primary key,
                source_id text not null,
                text text not null,
                embedding vector({EMBED_DIM}))"""
        )
        cur.execute(
            "create index if not exists kb_chunks_embedding_idx "
            "on kb_chunks using hnsw (embedding vector_cosine_ops)"
        )
        cur.execute(
            """create table if not exists experiments(
                id text primary key, name text not null, winner text,
                lift_pct double precision, significant boolean, summary text)"""
        )
        cur.execute(
            """create table if not exists followups(
                id bigserial primary key, title text not null, context text,
                created_at timestamptz default now())"""
        )
        cur.execute(
            """create table if not exists runs(
                id bigserial primary key, step_kind text, tool text,
                input jsonb, output text, at timestamptz default now())"""
        )
        conn.commit()


# --- kb_search ---------------------------------------------------------------
def _search_kb_sync(query: str, top_k: int) -> list[dict]:
    vec = embed_one(query)
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "select source_id, text from kb_chunks order by embedding <=> %s::vector limit %s",
            (vec_literal(vec), top_k),
        )
        return [{"source_id": r[0], "text": r[1]} for r in cur.fetchall()]


async def search_kb(query: str, top_k: int = 5) -> list[dict]:
    return await asyncio.to_thread(_search_kb_sync, query, top_k)


# --- experiment_lookup -------------------------------------------------------
def _experiment_sync(name_or_id: str) -> str | None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """select name, winner, lift_pct, significant, summary from experiments
               where id = %s or name ilike %s limit 1""",
            (name_or_id, f"%{name_or_id}%"),
        )
        r = cur.fetchone()
    if not r:
        return None
    name, winner, lift, sig, summ = r
    return f"{name}: winner={winner}, lift={lift}%, significant={sig}. {(summ or '').strip()}"


async def experiment_by_name(name_or_id: str) -> str | None:
    return await asyncio.to_thread(_experiment_sync, name_or_id)


# --- create_followup ---------------------------------------------------------
def _followup_sync(title: str, context: str) -> str:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "insert into followups(title, context) values(%s, %s) returning id",
            (title, context),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
    return str(new_id)


async def write_followup(title: str, context: str = "") -> str:
    return await asyncio.to_thread(_followup_sync, title, context)


# --- run tracing -------------------------------------------------------------
def _record_sync(step: "Step") -> None:
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute(
                "insert into runs(step_kind, tool, input, output, at) values(%s,%s,%s,%s,%s)",
                (
                    step.kind,
                    step.tool,
                    json.dumps(step.input) if step.input is not None else None,
                    step.output,
                    step.at,
                ),
            )
            conn.commit()
    except Exception:
        pass  # a trace write must never break the user's reply


async def record_step(step: "Step") -> None:
    await asyncio.to_thread(_record_sync, step)
