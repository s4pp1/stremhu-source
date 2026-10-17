from core.common.schemas.internal import SeriesInfo
from core.modules.kodi.schemas.api import (
    KodiImdbStreamsRequest,
)
from core.modules.torrent_streams.schemas import TorrentStream
from core.modules.torrent_streams.service import TorrentStreamsService
from core.modules.users.models import UserModel


class KodiService:
    def __init__(self, torrent_streams_service: TorrentStreamsService):
        self._torrent_streams_service = torrent_streams_service

    async def imdb_streams(
        self,
        user: UserModel,
        imdb_id: str,
        payload: KodiImdbStreamsRequest | None = None,
    ) -> tuple[list[TorrentStream], list[str]]:
        series: SeriesInfo | None = None
        if payload and payload.season is not None and payload.episode is not None:
            series = SeriesInfo(
                season=payload.season,
                episode=payload.episode,
            )

        torrent_streams, errors = await self._torrent_streams_service.find_by_imdb(
            user=user,
            imdb_id=imdb_id,
            series=series,
        )

        return torrent_streams, errors
