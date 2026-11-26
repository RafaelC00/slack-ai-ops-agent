"""Vercel entrypoint.

Vercel's @vercel/python runtime serves the ASGI ``app`` exported here. All
routes are forwarded to it by vercel.json.
"""

from app.main import app  # noqa: F401  (re-exported for the Vercel runtime)
