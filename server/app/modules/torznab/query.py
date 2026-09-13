import re
from dataclasses import dataclass
from datetime import date

from fastapi import Request

from app.modules.torznab.constants import (
    LIMIT_DEFAULT,
    LIMIT_MAX,
    UNIMPLEMENTED_FUNCTIONS,
)
from app.modules.torznab.enums import TorznabErrorCode, TorznabFunction
from app.modules.torznab.exceptions import TorznabProtocolError

_IMDB_ID = re.compile(r"tt([0-9]{7,10})", re.IGNORECASE)
_IMDB_ID_DIGITS = re.compile(r"[0-9]{7,10}")
_CATEGORIES = re.compile(r"[0-9]{1,18}(,[0-9]{1,18})*")
_NONNEGATIVE_INTEGER = re.compile(r"[0-9]{1,18}")
_SEASON = re.compile(r"[sS]?([0-9]{1,4})")
_EPISODE = re.compile(r"[eE]?([0-9]{1,6})")
_DAILY_EPISODE = re.compile(r"([0-9]{1,2})/([0-9]{1,2})")
_YEAR = re.compile(r"[0-9]{4}")


@dataclass(frozen=True, slots=True)
class TorznabQuery:
    function: TorznabFunction
    q: str | None = None
    imdb_id: str | None = None
    season: int | None = None
    episode: int | str | None = None
    year: int | None = None
    categories: tuple[int, ...] = ()
    offset: int = 0
    limit: int = LIMIT_DEFAULT


def _incorrect(name: str) -> TorznabProtocolError:
    return TorznabProtocolError(
        TorznabErrorCode.INCORRECT_PARAMETER,
        f"Incorrect parameter ({name})",
    )


def _collect(request: Request) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    categories: list[str] = []

    for raw_name, raw_value in request.query_params.multi_items():
        name = raw_name.casefold()

        if name == "cat":
            categories.append(raw_value)
        else:
            values[name] = raw_value

    return values, categories


def _parse_function(values: dict[str, str]) -> TorznabFunction:
    raw_function = values.get("t", "").strip().casefold()

    if not raw_function:
        raise TorznabProtocolError(
            TorznabErrorCode.MISSING_PARAMETER,
            "Missing parameter (t)",
        )

    try:
        return TorznabFunction(raw_function)
    except ValueError:
        if raw_function in UNIMPLEMENTED_FUNCTIONS:
            raise TorznabProtocolError(
                TorznabErrorCode.FUNCTION_NOT_AVAILABLE,
                f"Function not available ({raw_function})",
            ) from None

        raise TorznabProtocolError(
            TorznabErrorCode.NO_SUCH_FUNCTION,
            f"No such function ({raw_function})",
        ) from None


def _parse_categories(raw_categories: list[str]) -> tuple[int, ...]:
    categories: list[int] = []

    for group in raw_categories:
        if _CATEGORIES.fullmatch(group.strip()) is None:
            raise _incorrect("cat")

        categories.extend(int(category) for category in group.strip().split(","))

    return tuple(categories)


def _parse_nonnegative_int(values: dict[str, str], name: str, default: int) -> int:
    raw_value = values.get(name)

    if raw_value is None:
        return default

    value = raw_value.strip()

    if _NONNEGATIVE_INTEGER.fullmatch(value) is None:
        raise _incorrect(name)

    return int(value)


def _parse_imdb_id(values: dict[str, str]) -> str | None:
    raw_imdb_id = values.get("imdbid")

    if raw_imdb_id is None:
        return None

    normalized = raw_imdb_id.strip()

    match = _IMDB_ID.fullmatch(normalized)
    if match is not None:
        return f"tt{match.group(1)}"

    if _IMDB_ID_DIGITS.fullmatch(normalized):
        return f"tt{normalized}"

    raise _incorrect("imdbid")


def _parse_season(values: dict[str, str]) -> int | None:
    raw_season = values.get("season")

    if raw_season is None:
        return None

    match = _SEASON.fullmatch(raw_season.strip())
    if match is None:
        raise _incorrect("season")

    return int(match.group(1))


def _parse_episode(values: dict[str, str]) -> int | str | None:
    raw_episode = values.get("ep")

    if raw_episode is None:
        return None

    episode = raw_episode.strip()

    daily_match = _DAILY_EPISODE.fullmatch(episode)
    if daily_match is not None:
        month, day = (int(value) for value in daily_match.groups())
        return f"{month:02d}/{day:02d}"

    match = _EPISODE.fullmatch(episode)
    if match is None:
        raise _incorrect("ep")

    return int(match.group(1))


def _parse_year(values: dict[str, str]) -> int | None:
    raw_year = values.get("year")

    if raw_year is None:
        return None

    year = raw_year.strip()

    if _YEAR.fullmatch(year) is None:
        raise _incorrect("year")

    return int(year)


def _validate_scope(
    function: TorznabFunction,
    season: int | None,
    episode: int | str | None,
) -> None:
    if function is TorznabFunction.MOVIE and season is not None:
        raise _incorrect("season")

    if function is TorznabFunction.MOVIE and episode is not None:
        raise _incorrect("ep")

    if episode is not None and season is None:
        raise TorznabProtocolError(
            TorznabErrorCode.MISSING_PARAMETER,
            "Missing parameter (season)",
        )

    # A napi epizódos sorozatokat a Sonarr season=YYYY&ep=MM/DD formában kéri,
    # ilyenkor a season az évszám.
    if isinstance(episode, str) and season is not None:
        if _YEAR.fullmatch(str(season)) is None:
            raise _incorrect("season")

        month, day = (int(value) for value in episode.split("/", 1))

        try:
            date(season, month, day)
        except ValueError as error:
            raise _incorrect("ep") from error


def parse_torznab_query(request: Request) -> TorznabQuery:
    values, raw_categories = _collect(request)

    function = _parse_function(values)

    output = values.get("o", "").strip().casefold()
    if output not in {"", "xml"}:
        raise _incorrect("o")

    if function is TorznabFunction.CAPS:
        return TorznabQuery(function=function)

    season = _parse_season(values)
    episode = _parse_episode(values)
    _validate_scope(function, season, episode)

    q = (values.get("q") or "").strip()

    return TorznabQuery(
        function=function,
        q=q or None,
        imdb_id=_parse_imdb_id(values),
        season=season,
        episode=episode,
        year=_parse_year(values),
        categories=_parse_categories(raw_categories),
        offset=_parse_nonnegative_int(values, "offset", 0),
        limit=min(
            _parse_nonnegative_int(values, "limit", LIMIT_DEFAULT),
            LIMIT_MAX,
        ),
    )
