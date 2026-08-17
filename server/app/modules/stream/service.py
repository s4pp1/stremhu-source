import asyncio

from fastapi import HTTPException

from app.common.database import isolated_db_session
from app.common.keyed_lock import KeyedLock
from app.common.logger import logger
from app.common.schemas.internal import ImdbInfo
from app.modules.indexers.service import IndexersService
from app.modules.playback_histories.dependencies import (
    create_playback_histories_service,
)
from app.modules.playback_histories.schemas.internal import (
    PlaybackHistoryClientInfo,
    PlaybackHistoryCreate,
)
from app.modules.relay.entities import File
from app.modules.relay.service import RelayService
from app.modules.stream.schemas import (
    ParsedRangeHeader,
    StreamToken,
)
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.schemas import TorrentFileIdentifier
from app.modules.torrent_files.service import (
    TorrentFilesService,
    create_isolated,
    touch_isolated,
)
from app.modules.torrents.dependencies import (
    create_torrents_service,
)
from app.modules.torrents.schemas.internal import TorrentWithRelay
from app.modules.torrents.service import TorrentsService

torrent_locks = KeyedLock()
playback_history_lock = KeyedLock()

# A háttérben futó touch task-okra kell egy referencia, különben a GC elviheti őket
_touch_tasks: set[asyncio.Task[None]] = set()


class StreamService:
    def __init__(
        self,
        torrents_service: TorrentsService,
        torrent_files_service: TorrentFilesService,
        indexers_service: IndexersService,
        relay_service: RelayService,
    ):
        self._torrents_service = torrents_service
        self._torrent_files_service = torrent_files_service
        self._indexers_service = indexers_service
        self._relay_service = relay_service

    async def prepare_for_stream(
        self,
        range_header: str | None,
        indexer_id: str,
        torrent_id: str,
        file_index: int,
    ) -> tuple[ParsedRangeHeader, File]:
        # A touch csak egy LRU időbélyeg, a lejátszás nem függ tőle: nem várunk rá.
        # Ha zárolt az adatbázis, a thread végigüli a 10 mp-es busy timeoutot,
        # a range kérés viszont ettől függetlenül megy tovább.
        self._touch_in_background(
            TorrentFileIdentifier(indexer_id=indexer_id, torrent_id=torrent_id)
        )

        async with torrent_locks(f"{indexer_id}:{torrent_id}"):
            torrent_with_relay: TorrentWithRelay | None = await asyncio.to_thread(
                self._torrents_service.find_by_id,
                indexer_id=indexer_id,
                torrent_id=torrent_id,
            )

            if torrent_with_relay is None:
                torrent_file = await asyncio.to_thread(
                    self._torrent_files_service.find_by_id,
                    indexer_id=indexer_id,
                    torrent_id=torrent_id,
                )

                if torrent_file is None:
                    indexer_torrent = (
                        await self._indexers_service.get_torrent_by_torrent_id(
                            indexer_id=indexer_id, torrent_id=torrent_id
                        )
                    )
                    downloaded_torrent_file = (
                        await self._indexers_service.download_torrent(
                            indexer_id=indexer_id,
                            torrent_id=torrent_id,
                            download_url=indexer_torrent.download_url,
                        )
                    )

                    torrent_file = await asyncio.to_thread(
                        create_isolated,
                        indexer_id=indexer_id,
                        torrent_id=torrent_id,
                        torrent_bytes=downloaded_torrent_file.torrent_bytes,
                    )

                torrent_with_relay = await asyncio.to_thread(
                    self._create_torrent,
                    torrent_file=torrent_file,
                    file_index=file_index,
                )

        file = self._relay_service.get_torrent_file(
            info_hash=torrent_with_relay.info_hash,
            file_index=file_index,
        )

        parsed_range_header = self._parse_range_header(
            file_size=file.size,
            range_header=range_header,
        )

        return parsed_range_header, file

    async def save_playback_history(
        self,
        stream_token: StreamToken,
        client_info: PlaybackHistoryClientInfo,
        user_id: str,
        file: File,
        imdb_info: ImdbInfo | None = None,
    ) -> None:
        try:
            async with playback_history_lock(stream_token.playback_id):
                await asyncio.to_thread(
                    self._save_playback_history,
                    PlaybackHistoryCreate(
                        client=client_info,
                        indexer_id=stream_token.indexer_id,
                        playback_id=stream_token.playback_id,
                        user_id=user_id,
                        torrent_id=stream_token.torrent_id,
                        file_index=stream_token.file_index,
                        imdb_info=imdb_info,
                        torrent_name=file.torrent.name,
                        file_name=file.name,
                    ),
                )
        except Exception as e:
            logger.warning(f"Nem sikerült menteni a lejátszási előzményt: {e}")

    def _touch_in_background(self, identifier: TorrentFileIdentifier) -> None:
        task = asyncio.create_task(asyncio.to_thread(touch_isolated, identifier))
        _touch_tasks.add(task)
        task.add_done_callback(_touch_tasks.discard)

    def _save_playback_history(self, payload: PlaybackHistoryCreate) -> None:
        """Külön session: egy sikertelen írás nem viheti magával a kérés tranzakcióját."""
        with isolated_db_session() as local_db:
            create_playback_histories_service(local_db).get_or_create(payload)

    def _create_torrent(
        self,
        torrent_file: TorrentFileModel,
        file_index: int,
    ) -> TorrentWithRelay:
        # A validáció nem érinti az adatbázist: hibás fájl index miatt ne nyissunk
        # feleslegesen tranzakciót.
        self._validate_file(torrent_file, file_index)

        with isolated_db_session() as local_db:
            return create_torrents_service(local_db).create_from_torrent_file(
                torrent_file
            )

    def _validate_file(
        self,
        torrent_file: TorrentFileModel,
        file_index: int,
    ):
        if file_index not in range(len(torrent_file.info.files)):
            raise HTTPException(400, "Érvénytelen fájl index.")

        file_info = torrent_file.info.files[file_index]
        if not file_info.is_video:
            raise HTTPException(400, "A megadott fájl nem videó.")

    def _parse_range_header(
        self,
        file_size: int,
        range_header: str | None = None,
    ) -> ParsedRangeHeader:
        if range_header is None:
            return ParsedRangeHeader(
                start_byte=0,
                end_byte=file_size - 1,
                content_length=file_size,
            )

        if not range_header.startswith("bytes="):
            raise HTTPException(416, "Érvénytelen range header.")

        range_value = range_header.replace("bytes=", "", 1).strip()
        if "," in range_value:
            raise HTTPException(416, "A több tartomány nem támogatott.")

        start_byte_str, end_byte_str = range_value.split("-", 1)

        if start_byte_str == "":
            if not end_byte_str:
                raise HTTPException(416, "Érvénytelen range header.")

            suffix_length = int(end_byte_str)
            if suffix_length <= 0:
                raise HTTPException(416, "Érvénytelen range header.")

            start_byte = max(file_size - suffix_length, 0)
            end_byte = file_size - 1
        else:
            start_byte = int(start_byte_str)
            end_byte = int(end_byte_str) if end_byte_str else file_size - 1

        if (
            start_byte < 0
            or end_byte < 0
            or start_byte > end_byte
            or end_byte >= file_size
        ):
            raise HTTPException(416, "A kért tartomány kívül esik a fájlon.")

        content_length = end_byte - start_byte + 1

        return ParsedRangeHeader(
            start_byte=start_byte,
            end_byte=end_byte,
            content_length=content_length,
        )
