from enum import Enum


class ContentType(str, Enum):
    MOVIE = "movie"
    SERIES = "series"
    CHANNEL = "channel"
    TV = "tv"


class ShortManifestResource(str, Enum):
    CATALOG = "catalog"
    META = "meta"
    STREAM = "stream"
    SUBTITLES = "subtitles"
    ADDON_CATALOG = "addon_catalog"


class ExtraName(str, Enum):
    SEARCH = "search"
    GENRE = "genre"
    SKIP = "skip"


class PosterShape(str, Enum):
    SQUARE = "square"
    REGULAR = "regular"
    LANDSCAPE = "landscape"


class ManifestConfigType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    PASSWORD = "password"
    CHECKBOX = "checkbox"
    SELECT = "select"


class StreamIdType(str, Enum):
    TORRENT = "torrent"
    IMDB = "imdb"


class MediaType(str, Enum):
    MOVIE = "movie"
    SERIES = "series"
