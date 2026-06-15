import humanize
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.modules.attributes.schemas.api import AttributeResponse
from app.modules.indexer_definitions.schemas.internal import IndexerDefinition
from app.modules.torrent_streams.schemas import TorrentStream


class KodiImdbStreamsParams(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    season: int | None = Field(default=None, ge=1)
    episode: int | None = Field(default=None, ge=1)


class KodiMetaDto(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    value: str
    label: str


class KodiTrackerMetaDto(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    value: str
    label: str
    requires_full_download: bool
    url: str
    details_path: str


class KodiImdbStream(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    torrent_name: str
    file_name: str
    seeders: int | None = Field(default=0)
    size: str
    indexer: IndexerDefinition
    attributes: list[AttributeResponse] = []
    url: str


class KodiImdbStreams(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    streams: list[KodiImdbStream]
    errors: list[str]

    @classmethod
    def from_torrent_streams_pair(
        cls,
        torrent_streams: list[TorrentStream],
        errors: list[str],
    ) -> "KodiImdbStreams":
        kodi_streams = [
            KodiImdbStream(
                torrent_name=torrent_stream.torrent_name,
                file_name=torrent_stream.file_name,
                seeders=torrent_stream.seeders,
                size=humanize.naturalsize(torrent_stream.file_size, binary=True),
                indexer=IndexerDefinition.model_validate(
                    torrent_stream.indexer_account.indexer_definition
                ),
                attributes=[
                    AttributeResponse.model_validate(attribute)
                    for attribute in torrent_stream.attributes
                ],
                url=torrent_stream.play_url,
            )
            for torrent_stream in torrent_streams
        ]

        return KodiImdbStreams(
            streams=kodi_streams,
            errors=errors,
        )
