"""Detect calls to datasource.run_to_df that bypass RLSAwareSQLExecutor."""
from __future__ import annotations

import inspect
import logging

logger = logging.getLogger(__name__)

_RLS_EXECUTOR_CLASS = "RLSAwareSQLExecutor"


def warn_if_bypass(connector_method_name: str) -> None:
    """Log WARNING if the call stack does not go through RLSAwareSQLExecutor.

    Decorate RDBMSConnector.run_to_df to call this.
    v1: observe only, do not block.
    """
    stack = inspect.stack()
    for frame_info in stack:
        if _RLS_EXECUTOR_CLASS in frame_info.filename or _RLS_EXECUTOR_CLASS in (
            frame_info.function or ""
        ):
            return  # OK — called from executor
    caller = stack[2].function if len(stack) > 2 else "unknown"
    logger.warning(
        "BYPASS_RLS detected: %s called from %s without RLSAwareSQLExecutor",
        connector_method_name,
        caller,
    )
