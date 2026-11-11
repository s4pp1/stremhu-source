"""Step-by-step console output with per-step count progress.

With a TTY (`docker compose run`) this renders live rich progress bars; without
one (`docker compose up`, CI) it prints a line roughly every 10% so logs stay
readable.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TransferSpeedColumn,
)

console = Console(highlight=False)


class Counter:
    """Handle returned by `Steps.progress`; call `advance()` per item."""

    def __init__(self, label: str, total: int, *, unit: str, as_bytes: bool) -> None:
        self.label = label
        self.total = total
        self.done = 0
        self.unit = unit
        self.as_bytes = as_bytes
        self._progress: Progress | None = None
        self._task: TaskID | None = None
        self._last_print = 0.0
        self._last_pct = -1

    def advance(self, n: int = 1) -> None:
        self.done += n
        if self._progress is not None and self._task is not None:
            self._progress.update(self._task, advance=n)
            return
        # plain mode: print on each 10% step or every 5 seconds
        pct = int(self.done * 100 / self.total) if self.total else 100
        now = time.monotonic()
        if pct // 10 != self._last_pct // 10 or now - self._last_print > 5:
            self._last_pct = pct
            self._last_print = now
            console.print(
                f"      {self.label}: {self._fmt(self.done)}/{self._fmt(self.total)} {self.unit} ({pct}%)"
            )

    def _fmt(self, n: int) -> str:
        if not self.as_bytes:
            return str(n)
        size = float(n)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024
        return str(n)


class Steps:
    def __init__(self, total: int) -> None:
        self.total = total
        self.index = 0

    def start(self, title: str) -> None:
        self.index += 1
        console.print()
        console.print(f"[bold cyan][{self.index}/{self.total}][/] [bold]{title}[/]")

    def ok(self, message: str) -> None:
        console.print(f"      [green]✓[/] {message}")

    def note(self, message: str) -> None:
        console.print(f"      [dim]•[/] {message}")

    def warn(self, message: str) -> None:
        console.print(f"      [yellow]![/] {message}")

    def fail(self, message: str) -> None:
        console.print(f"      [red]✗[/] {message}")

    @contextmanager
    def progress(
        self, label: str, total: int, *, unit: str = "", as_bytes: bool = False
    ) -> Iterator[Counter]:
        counter = Counter(label, total, unit=unit, as_bytes=as_bytes)
        if total == 0:
            yield counter
            self.ok(f"{label}: nothing to do")
            return
        if not console.is_terminal:
            yield counter
            if counter._last_pct != 100:  # make sure the final state is printed
                console.print(
                    f"      {label}: {counter._fmt(counter.done)}/{counter._fmt(total)} {unit} (done)"
                )
            return
        columns = [
            TextColumn("      {task.description}"),
            BarColumn(bar_width=30),
        ]
        if as_bytes:
            columns += [DownloadColumn(), TransferSpeedColumn()]
        else:
            columns += [MofNCompleteColumn(), TaskProgressColumn()]
        columns.append(TimeElapsedColumn())
        with Progress(*columns, console=console, transient=False) as progress:
            counter._progress = progress
            counter._task = progress.add_task(label, total=total)
            yield counter
