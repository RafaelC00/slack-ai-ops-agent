"""Seed the knowledge base + experiments into Neon so the demo has real content.

Loads data/briefs/*.md and data/experiments.yaml, chunks + embeds the briefs
into kb_chunks, and loads the structured A/B results into experiments.

Run once after the DB exists:  python scripts/seed_kb.py
"""

from __future__ import annotations

import glob
import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.config import load_env  # noqa: E402

load_env()

from app.rag.embed import embed  # noqa: E402
from app.rag.store import _connect, init_schema, vec_literal  # noqa: E402

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"


def source_id(md: str, fallback: str) -> str:
    m = re.search(r"\*\*Source:\*\*\s*([\w-]+)", md)
    return m.group(1) if m else fallback


def chunk(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    text = text.strip()
    if len(text) <= size:
        return [text]
    out, i = [], 0
    while i < len(text):
        out.append(text[i : i + size])
        i += size - overlap
    return out


def main() -> int:
    init_schema()

    rows: list[tuple[str, str]] = []
    for f in sorted(glob.glob(str(DATA / "briefs" / "*.md"))):
        md = pathlib.Path(f).read_text(encoding="utf-8")
        sid = source_id(md, pathlib.Path(f).stem)
        for ch in chunk(md):
            rows.append((sid, ch))

    vectors = embed([t for _, t in rows])
    exps = yaml.safe_load((DATA / "experiments.yaml").read_text(encoding="utf-8"))["experiments"]

    with _connect() as conn, conn.cursor() as cur:
        cur.execute("truncate kb_chunks")
        for (sid, txt), vec in zip(rows, vectors):
            cur.execute(
                "insert into kb_chunks(source_id, text, embedding) values(%s,%s,%s::vector)",
                (sid, txt, vec_literal(vec)),
            )
        cur.execute("truncate experiments")
        for e in exps:
            cur.execute(
                """insert into experiments(id,name,winner,lift_pct,significant,summary)
                   values(%s,%s,%s,%s,%s,%s)""",
                (e["id"], e["name"], e.get("winner"), e.get("lift_pct"),
                 e.get("significant"), (e.get("summary") or "").strip()),
            )
        conn.commit()

    print(f"seeded {len(rows)} kb chunks from {len(set(s for s,_ in rows))} briefs, {len(exps)} experiments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
