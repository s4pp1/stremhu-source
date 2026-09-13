from enum import Enum, IntEnum


class TorznabFunction(str, Enum):
    CAPS = "caps"
    SEARCH = "search"
    MOVIE = "movie"
    TV_SEARCH = "tvsearch"


class TorznabErrorCode(IntEnum):
    INCORRECT_CREDENTIALS = 100
    MISSING_PARAMETER = 200
    INCORRECT_PARAMETER = 201
    NO_SUCH_FUNCTION = 202
    FUNCTION_NOT_AVAILABLE = 203
    UNKNOWN_ERROR = 900
