"""Slack request signature verification (v0 scheme).

This one is implemented fully — it's the security boundary of the service and
there's no reason to stub it. Reject anything older than 5 minutes (replay) or
whose HMAC doesn't match.
"""

from __future__ import annotations

import hashlib
import hmac
import time


def is_valid_slack_request(
    *,
    signing_secret: str,
    timestamp: str,
    signature: str,
    raw_body: bytes,
    max_age_seconds: int = 60 * 5,
) -> bool:
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False

    if abs(time.time() - ts) > max_age_seconds:
        return False  # stale → likely a replay

    basestring = b"v0:" + timestamp.encode() + b":" + raw_body
    computed = "v0=" + hmac.new(signing_secret.encode(), basestring, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature or "")
