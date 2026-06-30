"""Global token usage accumulator for per-iteration logging.

This module provides a lightweight, process-local counter that can be updated
by the LLM backend (backend/gpt.py) and snapshotted by the MCTS loop.

It is intentionally simple (no IO) so it works with nohup/background runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Tuple


@dataclass(frozen=True)
class UsageSnapshot:
    prompt_tokens: int
    completion_tokens: int


_lock = Lock()
_prompt_tokens = 0
_completion_tokens = 0


def add_usage(prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
    """Add token usage from a single model call."""
    global _prompt_tokens, _completion_tokens
    try:
        p = int(prompt_tokens or 0)
        c = int(completion_tokens or 0)
    except Exception:
        return
    with _lock:
        _prompt_tokens += p
        _completion_tokens += c


def snapshot() -> UsageSnapshot:
    """Take a snapshot of the current accumulated usage."""
    with _lock:
        return UsageSnapshot(prompt_tokens=_prompt_tokens, completion_tokens=_completion_tokens)


def delta_since(snap: UsageSnapshot) -> Tuple[int, int, int]:
    """Return (prompt_delta, completion_delta, total_delta) since a snapshot."""
    with _lock:
        dp = _prompt_tokens - snap.prompt_tokens
        dc = _completion_tokens - snap.completion_tokens
    return dp, dc, dp + dc
