"""Loads versions.toml: the per-release knowledge the migrator runs on."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomllib

DEFAULT_PATH = Path(__file__).with_name("versions.toml")


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Layout:
    name: str
    description: str
    database: str
    torrents: str
    resumes: str
    downloads: str

    def top_level(self) -> list[str]:
        """Top-level entries in /app/data that hold this layout's system data."""
        names: list[str] = []
        for rel in (self.database, self.torrents, self.resumes):
            first = Path(rel).parts[0]
            if first not in names:
                names.append(first)
        return names


@dataclass(frozen=True)
class VersionProfile:
    releases: str
    last_migration: str
    layout: str
    resume_data: bool
    trackers: tuple[str, ...]
    notes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SettingKey:
    to: str
    default: Any


@dataclass
class Config:
    path: Path
    verified_against: str
    layouts: dict[str, Layout]
    versions: list[VersionProfile]
    unsupported_message: str
    preferences: dict[str, str]
    values: dict[str, dict[str, list[str]]]
    system_settings: dict[str, SettingKey]
    relay_settings: dict[str, SettingKey]
    dropped_settings: dict[str, str]
    network: dict[str, Any] = field(default_factory=dict)

    def profile_for(self, last_migration: str | None) -> VersionProfile | None:
        for v in self.versions:
            if v.last_migration == last_migration:
                return v
        return None

    @property
    def supported_range(self) -> str:
        return f"{self.versions[0].releases.split('–')[0].strip()} – {self.versions[-1].releases.split('–')[-1].strip()}"


def _require(d: dict, key: str, where: str) -> Any:
    if key not in d:
        raise ConfigError(f"{where}: missing '{key}'")
    return d[key]


def load(path: Path | None = None) -> Config:
    path = path or Path(os.environ.get("MIGRATOR_CONFIG") or DEFAULT_PATH)
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}")
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: invalid TOML: {e}")

    if raw.get("schema") != 1:
        raise ConfigError(
            f"{path}: unsupported schema {raw.get('schema')!r} (expected 1)"
        )

    layouts = {
        name: Layout(
            name=name,
            description=entry.get("description", ""),
            database=_require(entry, "database", f"layouts.{name}"),
            torrents=_require(entry, "torrents", f"layouts.{name}"),
            resumes=_require(entry, "resumes", f"layouts.{name}"),
            downloads=entry.get("downloads", "downloads"),
        )
        for name, entry in _require(raw, "layouts", str(path)).items()
    }

    versions: list[VersionProfile] = []
    seen: set[str] = set()
    for i, v in enumerate(_require(raw, "versions", str(path))):
        where = f"versions[{i}]"
        profile = VersionProfile(
            releases=_require(v, "releases", where),
            last_migration=_require(v, "last_migration", where),
            layout=_require(v, "layout", where),
            resume_data=bool(_require(v, "resume_data", where)),
            trackers=tuple(v.get("trackers", [])),
            notes=tuple(v.get("notes", [])),
            warnings=tuple(v.get("warnings", [])),
        )
        if profile.layout not in layouts:
            raise ConfigError(f"{where}: unknown layout '{profile.layout}'")
        if profile.last_migration in seen:
            raise ConfigError(
                f"{where}: duplicate last_migration '{profile.last_migration}'"
            )
        seen.add(profile.last_migration)
        versions.append(profile)
    if not versions:
        raise ConfigError(f"{path}: no [[versions]] defined")

    preferences = dict(_require(raw, "preferences", str(path)))
    values = {
        k: {str(vk): list(vv) for vk, vv in v.items()}
        for k, v in _require(raw, "values", str(path)).items()
    }
    for old, new in preferences.items():
        if new not in values:
            raise ConfigError(
                f"preferences.{old} -> '{new}' has no [values.{new}] table"
            )

    settings = _require(raw, "settings", str(path))

    def keys(section: str) -> dict[str, SettingKey]:
        return {
            k: SettingKey(
                to=_require(v, "to", f"settings.{section}.{k}"),
                default=v.get("default"),
            )
            for k, v in _require(settings, section, "settings").items()
        }

    return Config(
        path=path,
        verified_against=str(raw.get("target", {}).get("verified_against", "")),
        layouts=layouts,
        versions=versions,
        unsupported_message=raw.get("unsupported", {}).get(
            "message", "This release is not supported."
        ),
        preferences=preferences,
        values=values,
        system_settings=keys("system"),
        relay_settings=keys("relay"),
        dropped_settings=dict(settings.get("dropped", {})),
        network=dict(settings.get("network", {})),
    )
