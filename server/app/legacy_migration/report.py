"""Migration report: what was migrated, what changed, what was lost."""

from __future__ import annotations

import datetime as dt
import json
from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

LEVELS = ("lossy", "warn", "info")
LEVEL_TITLES = {
    "lossy": "Lossy — data that could not be carried over",
    "warn": "Warnings — needs your attention",
    "info": "Notes — changed on the way, nothing lost",
}


@dataclass
class Entry:
    level: str
    section: str
    message: str


@dataclass
class Report:
    started_at: dt.datetime = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )
    finished_at: dt.datetime | None = None
    status: str = "running"
    context: dict[str, Any] = field(default_factory=dict)
    counts: OrderedDict[str, dict[str, int]] = field(default_factory=OrderedDict)
    entries: list[Entry] = field(default_factory=list)

    # ---- recording -------------------------------------------------------- #

    def lossy(self, section: str, message: str) -> None:
        self.entries.append(Entry("lossy", section, message))

    def warn(self, section: str, message: str) -> None:
        self.entries.append(Entry("warn", section, message))

    def info(self, section: str, message: str) -> None:
        self.entries.append(Entry("info", section, message))

    def action(self, section: str, message: str) -> None:
        """Something the user has to do when starting the new container."""
        self.entries.append(Entry("action", section, message))

    def count(
        self,
        entity: str,
        *,
        source: int | None = None,
        migrated: int | None = None,
        skipped: int | None = None,
    ) -> None:
        row = self.counts.setdefault(entity, {"source": 0, "migrated": 0, "skipped": 0})
        if source is not None:
            row["source"] = source
        if migrated is not None:
            row["migrated"] = migrated
        if skipped is not None:
            row["skipped"] = skipped

    def bump(self, entity: str, key: str, n: int = 1) -> None:
        row = self.counts.setdefault(entity, {"source": 0, "migrated": 0, "skipped": 0})
        row[key] = row.get(key, 0) + n

    def by_level(self, level: str) -> list[Entry]:
        return [e for e in self.entries if e.level == level]

    @property
    def is_lossy(self) -> bool:
        return any(e.level == "lossy" for e in self.entries)

    # ---- output ----------------------------------------------------------- #

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "lossy": self.is_lossy,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "context": self.context,
            "counts": self.counts,
            "next_steps": [asdict(e) for e in self.by_level("action")],
            "entries": [asdict(e) for e in self.entries if e.level != "action"],
        }

    def to_markdown(self) -> str:
        lines: list[str] = []
        lines.append("# StremHU Source · legacy data migration report")
        lines.append("")
        verdict = {
            "success": "✅ Completed"
            + (" — **lossy**, see below" if self.is_lossy else " — lossless"),
            "dry-run": "🧪 Dry run — nothing was changed"
            + (" (would be **lossy**)" if self.is_lossy else ""),
            "failed": "❌ Failed — see the error below; the source data was not modified",
        }.get(self.status, self.status)
        lines.append(f"**Result:** {verdict}")
        lines.append("")
        for key, value in self.context.items():
            lines.append(f"- **{key}:** {value}")
        lines.append(f"- **Started:** {self.started_at:%Y-%m-%d %H:%M:%S} UTC")
        if self.finished_at:
            lines.append(f"- **Finished:** {self.finished_at:%Y-%m-%d %H:%M:%S} UTC")
        lines.append("")

        actions = self.by_level("action")
        if actions:
            lines.append("## What to do next")
            lines.append("")
            for e in actions:
                lines.append(f"- **{e.section}:** {e.message}")
            lines.append("")

        if self.counts:
            lines.append("## Counts")
            lines.append("")
            lines.append("| Entity | In source | Migrated | Skipped |")
            lines.append("|---|---:|---:|---:|")
            for entity, row in self.counts.items():
                lines.append(
                    f"| {entity} | {row.get('source', 0)} | {row.get('migrated', 0)} | {row.get('skipped', 0)} |"
                )
            lines.append("")

        for level in LEVELS:
            entries = self.by_level(level)
            lines.append(f"## {LEVEL_TITLES[level]} ({len(entries)})")
            lines.append("")
            if not entries:
                lines.append("_None._")
                lines.append("")
                continue
            sections: OrderedDict[str, list[str]] = OrderedDict()
            for e in entries:
                sections.setdefault(e.section, []).append(e.message)
            for section, messages in sections.items():
                lines.append(f"### {section}")
                lines.append("")
                for m in messages:
                    lines.append(f"- {m}")
                lines.append("")

        lines.append("## Not migrated by design")
        lines.append("")
        lines.append(
            "- Web UI login sessions: log in again with the same username and password."
        )
        lines.append(
            "- Pairings that were still pending: pair that device again. Already-paired devices keep working, because they hold the user's API key, which is migrated."
        )
        lines.append(
            "- Network/HTTPS settings: the new app sets these up on first start from `HOST_IP` / `REVERSE_PROXY_DOMAIN` (see *What to do next*)."
        )
        lines.append("")
        return "\n".join(lines)

    def write(self, directory: Path) -> tuple[Path, Path]:
        directory.mkdir(parents=True, exist_ok=True)
        md = directory / "report.md"
        js = directory / "report.json"
        md.write_text(self.to_markdown(), encoding="utf-8")
        js.write_text(
            json.dumps(self.to_json(), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return md, js
