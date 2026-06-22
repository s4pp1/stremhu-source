import humanize
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.modules.attributes.schemas.api import AttributeResponse
from app.modules.indexer_definitions.schemas.api import IndexerDefinitionResponse
from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.torrent_streams.schemas import TorrentStream


class KodiImdbStreamsRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    season: int | None = Field(default=None, ge=0)
    episode: int | None = Field(default=None, ge=1)


class KodiImdbStreamResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    torrent_name: str
    file_name: str
    seeders: int
    size: str
    indexer: IndexerDefinitionResponse
    media_attributes: list[AttributeResponse]
    url: str


class KodiImdbStreamsResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    streams: list[KodiImdbStreamResponse]
    errors: list[str]

    @classmethod
    def from_torrent_streams_pair(
        cls,
        torrent_streams: list[TorrentStream],
        errors: list[str],
    ) -> "KodiImdbStreamsResponse":
        kodi_streams = [
            KodiImdbStreamResponse(
                torrent_name=torrent_stream.torrent_name,
                file_name=torrent_stream.file_name,
                seeders=torrent_stream.seeders or 0,
                size=humanize.naturalsize(torrent_stream.file_size, binary=True),
                indexer=IndexerDefinitionResponse.model_validate(
                    torrent_stream.indexer_account.indexer_definition
                ),
                media_attributes=[
                    AttributeResponse.model_validate(attribute)
                    for attribute in torrent_stream.attributes
                    if isinstance(attribute, MediaAttributeModel)
                ],
                url=torrent_stream.play_url,
            )
            for torrent_stream in torrent_streams
        ]

        return KodiImdbStreamsResponse(
            streams=kodi_streams,
            errors=errors,
        )
