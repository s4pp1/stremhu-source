import pytest
from fastapi import Request

from app.modules.torznab.constants import LIMIT_DEFAULT, LIMIT_MAX
from app.modules.torznab.enums import TorznabErrorCode, TorznabFunction
from app.modules.torznab.exceptions import TorznabProtocolError
from app.modules.torznab.query import parse_torznab_query


def build_request(query_string: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/torznab/api",
            "headers": [],
            "query_string": query_string.encode(),
        }
    )


def parse(query_string: str):
    return parse_torznab_query(build_request(query_string))


def expect_error(query_string: str) -> TorznabProtocolError:
    with pytest.raises(TorznabProtocolError) as error:
        parse(query_string)

    return error.value


def test_missing_function():
    assert expect_error("apikey=x").code == TorznabErrorCode.MISSING_PARAMETER


def test_undefined_function():
    assert expect_error("t=nonsense").code == TorznabErrorCode.NO_SUCH_FUNCTION


@pytest.mark.parametrize("function", ["music", "book", "details", "getnfo", "get"])
def test_functions_defined_by_the_spec_but_not_implemented(function: str):
    """A specifikáció szerint ezekre 203 jár, nem 202."""
    assert expect_error(f"t={function}").code == (
        TorznabErrorCode.FUNCTION_NOT_AVAILABLE
    )


def test_function_names_are_case_insensitive():
    assert parse("T=TVSEARCH").function is TorznabFunction.TV_SEARCH


def test_caps_ignores_search_parameters():
    query = parse("t=caps&q=foo&limit=5")

    assert query.function is TorznabFunction.CAPS
    assert query.q is None
    assert query.limit == LIMIT_DEFAULT


def test_json_output_is_rejected():
    assert expect_error("t=search&o=json").code == TorznabErrorCode.INCORRECT_PARAMETER


@pytest.mark.parametrize(
    "value,expected",
    [
        ("tt0903747", "tt0903747"),
        ("TT0903747", "tt0903747"),
        ("0903747", "tt0903747"),
    ],
)
def test_imdb_id_is_normalised(value: str, expected: str):
    assert parse(f"t=movie&imdbid={value}").imdb_id == expected


@pytest.mark.parametrize("value", ["tt123", "abc", "tt09037470000"])
def test_invalid_imdb_id(value: str):
    assert expect_error(f"t=movie&imdbid={value}").code == (
        TorznabErrorCode.INCORRECT_PARAMETER
    )


def test_categories_from_repeated_parameters():
    query = parse("t=search&cat=2000,2040&cat=5000")

    assert query.categories == (2000, 2040, 5000)


@pytest.mark.parametrize("value", ["2000,abc", "", "2000,", "-1"])
def test_invalid_categories(value: str):
    assert expect_error(f"t=search&cat={value}").code == (
        TorznabErrorCode.INCORRECT_PARAMETER
    )


def test_limit_is_capped_to_the_advertised_maximum():
    assert parse(f"t=search&limit={LIMIT_MAX + 500}").limit == LIMIT_MAX


@pytest.mark.parametrize("query_string", ["t=search&limit=-1", "t=search&offset=x"])
def test_invalid_paging(query_string: str):
    assert expect_error(query_string).code == TorznabErrorCode.INCORRECT_PARAMETER


def test_season_and_episode_prefixes_are_accepted():
    query = parse("t=tvsearch&season=S01&ep=E02")

    assert (query.season, query.episode) == (1, 2)


def test_daily_episode_is_kept_as_month_and_day():
    query = parse("t=tvsearch&season=2024&ep=6/1")

    assert (query.season, query.episode) == (2024, "06/01")


def test_invalid_daily_episode_date():
    error = expect_error("t=tvsearch&season=2024&ep=2/31")

    assert error.description == "Incorrect parameter (ep)"


def test_daily_episode_without_a_year_blames_the_season():
    error = expect_error("t=tvsearch&season=1&ep=6/1")

    assert error.description == "Incorrect parameter (season)"


def test_episode_without_season_is_rejected():
    error = expect_error("t=tvsearch&ep=2")

    assert error.code == TorznabErrorCode.MISSING_PARAMETER
    assert error.description == "Missing parameter (season)"


@pytest.mark.parametrize(
    "query_string,parameter",
    [("t=movie&season=1", "season"), ("t=movie&ep=3", "ep")],
)
def test_movie_search_rejects_series_scope(query_string: str, parameter: str):
    error = expect_error(query_string)

    assert error.code == TorznabErrorCode.INCORRECT_PARAMETER
    assert error.description == f"Incorrect parameter ({parameter})"


def test_blank_query_is_dropped():
    assert parse("t=search&q=%20%20").q is None
