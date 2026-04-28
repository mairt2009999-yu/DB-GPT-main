"""Utilities for startup observability and success markers."""

from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Generator, List, Optional, Sequence, TextIO

_DISABLE_VALUES = {"0", "false", "off", "no"}


@dataclass
class StartupStage:
    """A completed startup stage timing."""

    name: str
    elapsed: float


def is_startup_timing_enabled() -> bool:
    """Return whether detailed startup timing logs are enabled."""
    value = os.getenv("DBGPT_STARTUP_TIMING")
    if value is None:
        return True
    return value.strip().lower() not in _DISABLE_VALUES


def resolve_callable_name(handler: Callable) -> str:
    """Build a readable name for an event handler/callable."""
    module_name = getattr(handler, "__module__", None)
    qualname = getattr(handler, "__qualname__", None) or getattr(
        handler, "__name__", None
    )
    if module_name and qualname:
        return f"{module_name}.{qualname}"
    return repr(handler)


def write_startup_line(
    service_name: str, message: str, output: Optional[TextIO] = None
) -> None:
    """Print one startup timing line with a consistent prefix."""
    sink = output or sys.stdout
    sink.write(f"[startup][{service_name}] {message}\n")
    sink.flush()


def write_startup_summary(
    service_name: str,
    stages: Sequence[StartupStage],
    *,
    title: str = "stage summary",
    output: Optional[TextIO] = None,
) -> None:
    """Print a startup stage timing summary."""
    write_startup_line(service_name, f"{title}:", output=output)
    for stage in stages:
        write_startup_line(
            service_name,
            f"  {stage.name}: {stage.elapsed:.3f}s",
            output=output,
        )


class StartupProfiler:
    """Collect and print startup stage timings for service bootstrapping."""

    _DISABLE_VALUES = {"0", "false", "off", "no"}

    def __init__(
        self,
        service_name: str,
        *,
        output: Optional[TextIO] = None,
        clock: Optional[Callable[[], float]] = None,
        detailed_timing: Optional[bool] = None,
    ):
        self.service_name = service_name
        self._output = output or sys.stdout
        self._clock = clock or time.perf_counter
        if detailed_timing is None:
            detailed_timing = self._is_detailed_timing_enabled()
        self._detailed_timing = detailed_timing
        self._stages: List[StartupStage] = []
        self._start_time = self._clock()
        self._ready_printed = False

    def _is_detailed_timing_enabled(self) -> bool:
        return is_startup_timing_enabled()

    def _print_line(self, message: str, *, add_prefix: bool = True) -> None:
        if add_prefix:
            write_startup_line(self.service_name, message, output=self._output)
            return
        self._output.write(message + "\n")
        self._output.flush()

    @contextmanager
    def stage(self, name: str) -> Generator[None, None, None]:
        """Measure a startup stage and print begin/end logs if enabled."""

        begin = self._clock()
        if self._detailed_timing:
            self._print_line(f">>> {name}")
        try:
            yield
        finally:
            elapsed = self._clock() - begin
            self._stages.append(StartupStage(name=name, elapsed=elapsed))
            if self._detailed_timing:
                self._print_line(f"<<< {name} | {elapsed:.3f}s")

    def mark_ready(self, host: Optional[str] = None, port: Optional[int] = None) -> bool:
        """Print startup success marker once.

        Returns:
            bool: True if the success marker is printed in this call.
        """
        if self._ready_printed:
            return False
        self._ready_printed = True

        total_elapsed = self._clock() - self._start_time
        if self._detailed_timing and self._stages:
            write_startup_summary(
                self.service_name,
                self._stages,
                output=self._output,
            )

        endpoint = "unknown"
        if host is not None and port is not None:
            endpoint = f"{host}:{port}"

        banner_lines = [
            "",
            "######################################################################",
            "#                        DB-GPT BOOT READY                           #",
            "######################################################################",
        ]
        for line in banner_lines:
            self._print_line(line, add_prefix=False)

        self._print_line(
            f"[STARTUP SUCCESS] {self.service_name} ready at {endpoint} | "
            f"total: {total_elapsed:.3f}s",
            add_prefix=False,
        )
        return True


def register_startup_success_handler(
    app,
    profiler: Optional[StartupProfiler],
    host: Optional[str],
    port: Optional[int],
) -> None:
    """Register startup callback that prints a success marker."""

    if profiler is None:
        return

    from dbgpt.util.fastapi import register_event_handler

    async def _on_startup_success() -> None:
        profiler.mark_ready(host=host, port=port)

    register_event_handler(app, "startup", _on_startup_success)
