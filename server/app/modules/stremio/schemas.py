from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import humanize
from pydantic import AfterValidator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from pydash import compact

from app.common.schemas.internal import ImdbInfo, SeriesInfo
from app.common.validators import validate_numeric_media_id
from app.modules.media_attributes.constants import MediaAttributeKey
from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.media_attributes.parser import clean_torrent_name
from app.modules.preferences.constants import PreferenceKey
from app.modules.preferences.seeds import DEFAULT_PREFERENCES
from app.modules.stremio.constants import ADDON_APP_PREFIX_ID
from app.modules.stremio.enums import (
    ContentType,
    ExtraName,
    ManifestConfigType,
    PosterShape,
    ShortManifestResource,
    StreamIdType,
)
from app.modules.torrent_files.schemas import TorrentFileSnapshot

if TYPE_CHECKING:
    from app.modules.torrent_streams.schemas import TorrentStream

# A helyben már letöltött fájl jelölése a stream nevében és leírásában
DOWNLOADED_MARKER = "⚡ Letöltve"
DOWNLOADED_BANNER = "⚡ Helyben tárolva (Azonnali lejátszás)"

# ──────────────────────────────────────────────
# Manifest schemas
# ──────────────────────────────────────────────


class ManifestExtra(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    name: ExtraName
    is_required: bool | None = None
    options: list[str] | None = None
    options_limit: int | None = None


class ManifestCatalog(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    type: ContentType
    id: str
    name: str
    extra: list[ManifestExtra] | None = None


class ManifestBehaviorHints(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    adult: bool | None = None
    p2p: bool | None = None
    configurable: bool | None = None
    configuration_required: bool | None = None


class ManifestConfig(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    key: str
    type: ManifestConfigType
    default: str | None = None
    title: str | None = None
    options: list[str] | None = None
    required: str | None = None


class FullManifestResource(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    name: ShortManifestResource
    types: list[ContentType]
    id_prefixes: list[str] | None = None


class Manifest(BaseModel):
    """Stremio addon manifest - https://stremio.github.io/stremio-addon-guide/"""

    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    id: str
    name: str
    description: str
    version: str
    resources: list[ShortManifestResource | FullManifestResource]
    types: list[ContentType]
    id_prefixes: list[str] | None = None
    catalogs: list[ManifestCatalog]
    addon_catalogs: list[ManifestCatalog] | None = None
    config: list[ManifestConfig] | None = None
    background: str | None = None
    logo: str | None = None
    contact_email: str | None = None
    behavior_hints: ManifestBehaviorHints | None = None


# ──────────────────────────────────────────────
# Stream schemas
# ──────────────────────────────────────────────

EMOJI_MAP = {
    pref.id: pref.emoji for pref in DEFAULT_PREFERENCES if getattr(pref, "emoji", None)
}


class BehaviorHints(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    country_whitelist: list[str] | None = None
    not_web_ready: bool = True
    binge_group: str | None = None
    filename: str | None = None
    video_size: int | None = None


class StremioSubtitle(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    id: str
    url: str
    lang: str
    label: str | None = None


class StremioStream(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    name: str
    description: str
    url: str | None = None
    external_url: str | None = None
    subtitles: list[StremioSubtitle] | None = None
    behavior_hints: BehaviorHints | None = None

    @classmethod
    def from_id_torrent_stream(
        cls,
        torrent_stream: TorrentStream,
        show_downloaded_marker: bool = True,
    ) -> StremioStream:
        file_size = f"💾 {humanize.naturalsize(torrent_stream.file_size, binary=True, format='%.2f')}"
        is_marked = show_downloaded_marker and torrent_stream.is_persisted_torrent

        stremio_subtitles = (
            [
                StremioSubtitle(
                    id=sub.id,
                    url=sub.url,
                    lang=sub.lang,
                    label=sub.label,
                )
                for sub in torrent_stream.subtitles
            ]
            if torrent_stream.subtitles
            else None
        )

        return cls(
            name=" | ".join(compact([DOWNLOADED_MARKER if is_marked else None, file_size])),
            description="\n".join(
                compact(
                    [
                        DOWNLOADED_BANNER if is_marked else None,
                        f"📁 {torrent_stream.file_name}",
                    ]
                )
            ),
            url=torrent_stream.play_url,
            subtitles=stremio_subtitles,
            behavior_hints=BehaviorHints(
                filename=cls._build_behavior_filename(
                    file_name=torrent_stream.file_name,
                    media_attributes=[
                        attr
                        for attr in torrent_stream.attributes
                        if isinstance(attr, MediaAttributeModel)
                    ],
                ),
                video_size=torrent_stream.file_size,
            ),
        )

    @classmethod
    def from_imdb_torrent_stream(
        cls,
        torrent_stream: TorrentStream,
        is_series: bool = False,
        show_downloaded_marker: bool = True,
    ) -> StremioStream:
        file_size = f"💾 {humanize.naturalsize(torrent_stream.file_size, binary=True, format='%.2f')}"
        is_marked = show_downloaded_marker and torrent_stream.is_persisted_torrent
        effective_seeders = (
            torrent_stream.combined_seeders
            if torrent_stream.combined_seeders is not None
            else torrent_stream.seeders
        )
        seeders = f"👥 {effective_seeders}" if effective_seeders is not None else None

        indexer_names = torrent_stream.extra_indexer_names or [
            torrent_stream.indexer_account.indexer_definition.name
        ]
        indexer = f"🧲 {', '.join(indexer_names)}"

        description_first_line = " | ".join(compact([indexer, seeders, file_size]))

        media_attributes = [
            attribute
            for attribute in torrent_stream.attributes
            if isinstance(attribute, MediaAttributeModel)
        ]

        flag_map = {
            MediaAttributeKey.HUN: "🇭🇺",
            MediaAttributeKey.ENG: "🇬🇧",
            "jap": "🇯🇵",
            "ger": "🇩🇪",
            "fra": "🇫🇷",
            "ita": "🇮🇹",
            "esp": "🇪🇸",
            "rus": "🇷🇺",
        }

        def format_group(pref_key: str) -> str | None:

            attrs = cls._attributes_parser(
                preference_id=pref_key,
                attributes=media_attributes,
            )

            if not attrs:
                return None

            if pref_key == PreferenceKey.LANGUAGE:
                parts = []
                for attr in attrs:
                    label = attr.short_name or attr.name
                    flag = flag_map.get(attr.id)
                    parts.append(f"{flag} {label}" if flag else label)
                return ", ".join(parts)

            joined = ", ".join([attr.short_name or attr.name for attr in attrs])
            emoji = EMOJI_MAP.get(pref_key)
            return f"{emoji} {joined}" if emoji else joined

        readable_resolutions = format_group(PreferenceKey.RESOLUTION)
        readable_audio_qualities = format_group(PreferenceKey.AUDIO_QUALITY)
        readable_video_qualities = format_group(PreferenceKey.VIDEO_QUALITY)
        readable_audio_spatials = format_group(PreferenceKey.AUDIO_SPATIAL)
        readable_language = format_group(PreferenceKey.LANGUAGE)
        readable_source = format_group(PreferenceKey.SOURCE)
        readable_editions = format_group(PreferenceKey.EDITION)
        readable_video_codecs = format_group(PreferenceKey.VIDEO_CODEC)
        readable_audio_channels = format_group(PreferenceKey.AUDIO_CHANNELS)

        readable_subtitle = "💬 🇭🇺 Felirat" if torrent_stream.has_hungarian_sub else None

        description_second_line = " | ".join(
            compact(
                [
                    readable_language,
                    readable_subtitle,
                    readable_audio_qualities,
                    readable_audio_spatials,
                    readable_audio_channels,
                ]
            )
        )

        description_third_line = " | ".join(
            compact(
                [
                    readable_editions,
                    readable_source,
                    readable_video_codecs,
                ]
            )
        )

        readable_is_persisted = DOWNLOADED_MARKER if is_marked else None

        name = " | ".join(
            compact(
                [readable_is_persisted, readable_resolutions, readable_video_qualities]
            )
        )
        persisted_banner = DOWNLOADED_BANNER if is_marked else None
        file_name_line = f"📁 {torrent_stream.file_name}" if is_series else None
        description = "\n".join(
            compact(
                [
                    persisted_banner,
                    file_name_line,
                    description_first_line,
                    description_second_line,
                    description_third_line,
                ]
            )
        )
        binge_group = f"{torrent_stream.indexer_account.indexer_definition.id}-{torrent_stream.torrent_id}"

        behavior_filename = cls._build_behavior_filename(
            file_name=torrent_stream.file_name,
            media_attributes=media_attributes,
        )

        stremio_subtitles = (
            [
                StremioSubtitle(
                    id=sub.id,
                    url=sub.url,
                    lang=sub.lang,
                    label=sub.label,
                )
                for sub in torrent_stream.subtitles
            ]
            if torrent_stream.subtitles
            else None
        )

        return cls(
            name=name,
            description=description,
            url=torrent_stream.play_url,
            subtitles=stremio_subtitles,
            behavior_hints=BehaviorHints(
                filename=behavior_filename,
                binge_group=binge_group,
                video_size=torrent_stream.file_size,
            ),
        )

    @classmethod
    def _build_behavior_filename(
        cls,
        file_name: str,
        media_attributes: list[MediaAttributeModel] | None = None,
    ) -> str:

        file_path = Path(file_name)
        extension = file_path.suffix
        stem = file_path.stem

        cleaned_stem = clean_torrent_name(stem)
        cleaned_stem = cleaned_stem.replace(" ", ".")
        cleaned_stem = re.sub(r"\.+", ".", cleaned_stem)
        cleaned_stem = cleaned_stem.replace(".-", "-").replace("-.", "-")
        cleaned_stem = cleaned_stem.strip(".")

        attributes_ids = ""
        if media_attributes:
            attributes_ids = ".".join(
                compact([f"{attr.id}" for attr in media_attributes])
            )

        if attributes_ids:
            return f"{cleaned_stem}.{attributes_ids}{extension}"
        return f"{cleaned_stem}{extension}"

    @classmethod
    def _attributes_parser(
        cls,
        preference_id: str,
        attributes: list[MediaAttributeModel],
    ) -> list[MediaAttributeModel]:
        return [
            attribute
            for attribute in attributes
            if attribute.preference_id == preference_id and attribute.show_in_details
        ]


class StremioStreams(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    streams: list[StremioStream]


class StremioSubtitles(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    subtitles: list[StremioSubtitle] = []



# ──────────────────────────────────────────────
# Catalog / Meta schemas
# ──────────────────────────────────────────────


class MetaLink(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    name: str
    category: str
    url: str


class MetaTrailer(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    yt_id: str
    description: str


class MetaVideo(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    id: str
    title: str
    released: str | None = None
    thumbnail: str | None = None
    available: bool | None = None
    episode: int | None = None
    season: int | None = None
    trailer: str | None = None
    overview: str | None = None


class BaseMeta(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    id: str
    imdb_id: str | None = None
    type: ContentType
    name: str
    poster: str | None = None
    poster_shape: PosterShape = PosterShape.REGULAR
    background: str | None = None
    logo: str | None = None
    description: str | None = None
    imdb_rating: str | None = None
    release_info: str | None = None
    genres: list[str] | None = None
    cast: list[str] | None = None
    director: list[str] | None = None
    links: list[MetaLink] | None = None

    @staticmethod
    def build_meta_id(indexer_id: str, torrent_id: str) -> str:
        return f"{ADDON_APP_PREFIX_ID}{indexer_id}:{torrent_id}"


class MetaPreview(BaseMeta):
    @classmethod
    def from_torrent_file(
        cls,
        torrent_file: TorrentFileSnapshot,
        content_type: ContentType = ContentType.MOVIE,
        imdb_id: str | None = None,
        imdb_rating: str | None = None,
    ) -> MetaPreview:
        poster = (
            f"https://images.metahub.space/poster/medium/{imdb_id}/img"
            if imdb_id
            else None
        )
        return cls(
            id=cls.build_meta_id(
                torrent_file.indexer_id,
                torrent_file.torrent_id,
            ),
            imdb_id=imdb_id,
            type=content_type,
            name=torrent_file.info.name,
            poster=poster,
            imdb_rating=imdb_rating,
        )


class MetaDetail(BaseMeta):
    released: str | None = None
    year: str | None = None
    trailers: list[MetaTrailer] | None = None
    videos: list[MetaVideo] | None = None
    runtime: str | None = None
    language: str | None = None
    country: str | None = None
    awards: str | None = None
    website: str | None = None
    behavior_hints: MetaDetailBehaviorHints | None = None
    writer: list[str] | None = None

    @classmethod
    def from_torrent_file(
        cls,
        torrent_file: TorrentFileSnapshot,
        content_type: ContentType = ContentType.MOVIE,
        imdb_id: str | None = None,
    ) -> MetaDetail:
        videos: list[MetaVideo] | None = None
        behavior_hints: MetaDetailBehaviorHints | None = None

        if content_type == ContentType.SERIES:
            from app.modules.torrent_streams.utils.resolver_helpers import (
                is_sample_or_trash,
            )
            from app.modules.torrent_streams.utils.series_parser import SeriesParser

            videos = []
            default_vid: str | None = None
            ep_counter = 1
            for file in torrent_file.info.files:
                if not file.is_video or is_sample_or_trash(file.name):
                    continue
                s_list, e_list = SeriesParser(file.path or file.name).parse()
                season = s_list[0] if s_list else 1
                episode = e_list[0] if e_list else ep_counter
                ep_counter += 1
                video_id = f"{cls.build_meta_id(torrent_file.indexer_id, torrent_file.torrent_id)}:{file.index}"
                if not default_vid:
                    default_vid = video_id
                videos.append(
                    MetaVideo(
                        id=video_id,
                        title=file.name,
                        season=season,
                        episode=episode,
                    )
                )
            if default_vid:
                behavior_hints = MetaDetailBehaviorHints(default_video_id=default_vid)

        poster = (
            f"https://images.metahub.space/poster/medium/{imdb_id}/img"
            if imdb_id
            else None
        )
        background = (
            f"https://live.metahub.space/background/medium/{imdb_id}/img"
            if imdb_id
            else None
        )

        return cls(
            id=cls.build_meta_id(
                torrent_file.indexer_id,
                torrent_file.torrent_id,
            ),
            imdb_id=imdb_id,
            type=content_type,
            name=torrent_file.info.name,
            poster=poster,
            background=background,
            videos=videos,
            behavior_hints=behavior_hints,
        )


class MetaDetailBehaviorHints(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    default_video_id: str | None = None
    has_scheduled_videos: bool | None = None


class StremioCatalogResponse(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    metas: list[MetaPreview]


class MetaResponse(BaseModel):
    meta: MetaDetail | dict


class StremioCache(BaseModel):
    cache_max_age: int | None = None
    stale_revalidate: int | None = None
    stale_error: int | None = None


class ParsedExtra(BaseModel):
    search: str | None = None
    genre: str | None = None
    skip: int | None = None


class ImdbStreamId(ImdbInfo):
    type: StreamIdType = StreamIdType.IMDB


class TorrentStreamId(BaseModel):
    type: StreamIdType = StreamIdType.TORRENT
    indexer_id: str
    torrent_id: str
    file_index: int | None = None


NumericMediaId = Annotated[str, AfterValidator(validate_numeric_media_id)]


class TvdbStreamId(BaseModel):
    type: StreamIdType = StreamIdType.TVDB
    tvdb_id: NumericMediaId
    series_info: SeriesInfo | None = None


class KitsuStreamId(BaseModel):
    type: StreamIdType = StreamIdType.KITSU
    kitsu_id: NumericMediaId
    episode: int | None = None
    series_info: SeriesInfo | None = None


class TmdbStreamId(BaseModel):
    type: StreamIdType = StreamIdType.TMDB
    tmdb_id: NumericMediaId
    series_info: SeriesInfo | None = None


class MalStreamId(BaseModel):
    type: StreamIdType = StreamIdType.MAL
    mal_id: NumericMediaId
    episode: int | None = None
    series_info: SeriesInfo | None = None


StreamId = (
    ImdbStreamId
    | TorrentStreamId
    | TvdbStreamId
    | KitsuStreamId
    | TmdbStreamId
    | MalStreamId
)



class ParsedCatalogId(BaseModel):
    indexer_id: str = ""
    torrent_id: str = ""
