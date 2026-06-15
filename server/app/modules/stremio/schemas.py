from __future__ import annotations

from typing import TYPE_CHECKING

import humanize
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from pydash import compact

from app.common.schemas.internal import ImdbInfo
from app.modules.media_attributes.models import MediaAttributeModel
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
from app.modules.torrent_files.models import TorrentFileModel

if TYPE_CHECKING:
    from app.modules.torrent_streams.schemas import TorrentStream

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


class StremioStream(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    name: str
    description: str
    url: str
    behavior_hints: BehaviorHints

    @classmethod
    def from_id_torrent_stream(cls, torrent_stream: TorrentStream) -> StremioStream:
        file_size = f"💾 {humanize.naturalsize(torrent_stream.file_size, binary=True, format='%.2f')}"

        return cls(
            name=file_size,
            description=f"📁 {torrent_stream.file_name}",
            url=torrent_stream.play_url,
            behavior_hints=BehaviorHints(
                filename=torrent_stream.file_name,
            ),
        )

    @classmethod
    def from_imdb_torrent_stream(
        cls,
        torrent_stream: TorrentStream,
    ) -> StremioStream:
        file_size = f"💾 {humanize.naturalsize(torrent_stream.file_size, binary=True, format='%.2f')}"
        seeders = f"👥 {torrent_stream.seeders}"
        indexer = f"🧲 {torrent_stream.indexer_account.indexer_definition.name}"

        description_first_line = " | ".join(compact([indexer, seeders, file_size]))

        def format_group(pref_key: str) -> str | None:
            attrs = cls._attributes_parser(
                preference_id=pref_key,
                attributes=torrent_stream.attributes,
            )
            if not attrs:
                return None
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

        description_second_line = " | ".join(
            compact(
                [
                    readable_language,
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

        readable_is_persisted: str | None = None

        if torrent_stream.is_persisted_torrent:
            readable_is_persisted = "⭐"

        name = " | ".join(
            compact(
                [readable_is_persisted, readable_resolutions, readable_video_qualities]
            )
        )
        description = "\n".join(
            [description_first_line, description_second_line, description_third_line]
        )
        binge_group = f"{torrent_stream.indexer_account.indexer_definition.id}-{torrent_stream.torrent_id}"

        return cls(
            name=name,
            description=description,
            url=torrent_stream.play_url,
            behavior_hints=BehaviorHints(
                filename=torrent_stream.file_name,
                binge_group=binge_group,
            ),
        )

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
        torrent_file: TorrentFileModel,
    ) -> MetaPreview:
        return cls(
            id=cls.build_meta_id(
                torrent_file.indexer_id,
                torrent_file.torrent_id,
            ),
            type=ContentType.MOVIE,
            name=torrent_file.info.name,
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
        torrent_file: TorrentFileModel,
    ) -> MetaDetail:
        return cls(
            id=cls.build_meta_id(
                torrent_file.indexer_id,
                torrent_file.torrent_id,
            ),
            type=ContentType.MOVIE,
            name=torrent_file.info.name,
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


StreamId = ImdbStreamId | TorrentStreamId


class ParsedCatalogId(BaseModel):
    indexer_id: str = ""
    torrent_id: str = ""
