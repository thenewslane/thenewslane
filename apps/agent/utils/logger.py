"""
utils/logger.py — Structured pipeline logger.

Writes to console (stdout) with a consistent timestamped format.
Optionally writes ERROR-level events to runs_log.error_message in Supabase.

Usage:
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("Signal collection started")

    # Attach Supabase after batch is created:
    from utils.logger import attach_supabase
    attach_supabase(batch_id="batch_abc123")
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

# ── Formatter ─────────────────────────────────────────────────────────────────


class StructuredFormatter(logging.Formatter):
    """
    Emits one JSON-like line per record:
        2025-02-21T14:00:00 [INFO ] nodes.signal_collector: Collected 42 signals  {'platform': 'twitter'}
    Falls back to plain text for non-dict extra payloads.
    """

    LEVEL_WIDTH = 8

    def format(self, record: logging.LogRecord) -> str:
        ts = self.formatTime(record, "%Y-%m-%dT%H:%M:%S")
        level = record.levelname.ljust(self.LEVEL_WIDTH)
        base = f"{ts} [{level}] {record.name}: {record.getMessage()}"

        # Attach any extra dict passed via the `extra` kwarg
        extra: dict[str, Any] = {
            k: v
            for k, v in record.__dict__.items()
            if k not in logging.LogRecord.__dict__
            and k not in ("message", "asctime", "args", "msg")
            and not k.startswith("_")
        }
        if extra:
            try:
                base += "  " + json.dumps(extra, default=str)
            except Exception:
                pass

        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)

        return base


# ── Supabase handler ──────────────────────────────────────────────────────────


class _SupabaseErrorHandler(logging.Handler):
    """
    On ERROR or CRITICAL records: updates runs_log.error_message for the
    current batch. Failures are silently swallowed — never let logging crash
    the pipeline.
    """

    def __init__(self, batch_id: str) -> None:
        super().__init__(logging.ERROR)
        self._batch_id = batch_id
        self._client: Any = None  # lazy import to avoid circular dependency

    def _get_client(self) -> Any:
        if self._client is None:
            from utils.supabase_client import db  # noqa: PLC0415

            self._client = db
        return self._client

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            self._get_client().log_run(
                self._batch_id,
                error_message=message[:2000],
            )
        except Exception:
            pass  # intentionally silent


# ── Root pipeline logger ──────────────────────────────────────────────────────

_ROOT_LOGGER_NAME = "agent"
_supabase_handler: _SupabaseErrorHandler | None = None


def _build_console_handler() -> logging.StreamHandler:  # type: ignore[type-arg]
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    handler.setLevel(logging.DEBUG)
    return handler


def _configure_root() -> logging.Logger:
    root = logging.getLogger(_ROOT_LOGGER_NAME)
    if root.handlers:
        return root  # already configured
    root.setLevel(logging.DEBUG)
    root.addHandler(_build_console_handler())
    root.propagate = False
    return root


_configure_root()


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger under the 'agent' namespace.

    >>> log = get_logger(__name__)
    >>> log.info("hello")
    """
    # Ensure the module name is prefixed with 'agent.' so hierarchy works
    if not name.startswith(_ROOT_LOGGER_NAME):
        name = f"{_ROOT_LOGGER_NAME}.{name.lstrip('.')}"
    return logging.getLogger(name)


def attach_supabase(batch_id: str) -> None:
    """
    Call once after a batch row has been created to enable Supabase error
    logging. Idempotent — calling again replaces the previous handler.
    """
    global _supabase_handler  # noqa: PLW0603
    root = logging.getLogger(_ROOT_LOGGER_NAME)

    # Remove old handler if present
    if _supabase_handler is not None:
        root.removeHandler(_supabase_handler)

    _supabase_handler = _SupabaseErrorHandler(batch_id)
    _supabase_handler.setFormatter(StructuredFormatter())
    root.addHandler(_supabase_handler)
    root.debug("Supabase error logging attached for batch %s", batch_id)


def detach_supabase() -> None:
    """Remove the Supabase handler (call at end of a batch run)."""
    global _supabase_handler  # noqa: PLW0603
    if _supabase_handler is not None:
        logging.getLogger(_ROOT_LOGGER_NAME).removeHandler(_supabase_handler)
        _supabase_handler = None
