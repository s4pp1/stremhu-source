from fastapi import HTTPException

from app.common.async_utils import owned_to_thread
from app.common.database import isolated_db_session
from app.common.keyed_lock import KeyedLock
from app.common.log_safety import network_error_fields
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
from app.modules.torrent_files.isolated_service import IsolatedTorrentFilesService
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_files.schemas import TorrentFileIdentifier
from app.modules.torrent_files.service import TorrentFilesService
from app.modules.torrents.dependencies import (
    create_torrents_service,
)
from app.modules.torrents.schemas.internal import TorrentWithRelay
from app.modules.torrents.service import TorrentsService

torrent_locks = KeyedLock()
playback_history_lock = KeyedLock()


class StreamService:
    def __init__(
        self,
        torrents_service: TorrentsService,
        torrent_files_service: TorrentFilesService,
        indexers_service: IndexersService,
        relay_service: RelayService,
        isolated_torrent_files_service: IsolatedTorrentFilesService,
    ):
        self._torrents_service = torrents_service
        self._torrent_files_service = torrent_files_service
        self._indexers_service = indexers_service
        self._relay_service = relay_service
        self._isolated_torrent_files_service = isolated_torrent_files_service

    async def prepare_for_stream(
        self,
        range_header: str | None,
        indexer_id: str,
        torrent_id: str,
        file_index: int,
        require_subtitle: bool = False,
    ) -> tuple[ParsedRangeHeader, File]:
        self._isolated_torrent_files_service.touch(
            TorrentFileIdentifier(indexer_id=indexer_id, torrent_id=torrent_id)
        )

        async with torrent_locks(f"{indexer_id}:{torrent_id}"):
            torrent_with_relay: TorrentWithRelay | None = await owned_to_thread(
                self._torrents_service.find_by_id,
                indexer_id=indexer_id,
                torrent_id=torrent_id,
            )

            if torrent_with_relay is None:
                torrent_file = await owned_to_thread(
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

                    torrent_file = await owned_to_thread(
                        self._isolated_torrent_files_service.create,
                        indexer_id=indexer_id,
                        torrent_id=torrent_id,
                        torrent_bytes=downloaded_torrent_file.torrent_bytes,
                    )

                torrent_with_relay = await owned_to_thread(
                    self._create_torrent,
                    torrent_file=torrent_file,
                    file_index=file_index,
                    require_subtitle=require_subtitle,
                )

        file = self._relay_service.get_torrent_file(
            info_hash=torrent_with_relay.info_hash,
            file_index=file_index,
        )

        # A már relayben lévő torrentnél is ugyanaz a típusszabály érvényes.
        validate_file_type(
            is_video=file.is_video,
            is_subtitle=file.is_subtitle,
            require_subtitle=require_subtitle,
        )

        parsed_range_header = parse_range_header(
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
                await owned_to_thread(
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
            logger.warning("operation=playback-history-write %s", network_error_fields(e))

    def _save_playback_history(self, payload: PlaybackHistoryCreate) -> None:
        """Külön session: egy sikertelen írás nem viheti magával a kérés tranzakcióját."""
        with isolated_db_session() as local_db:
            create_playback_histories_service(local_db).get_or_create(payload)

    def _create_torrent(
        self,
        torrent_file: TorrentFileModel,
        file_index: int,
        require_subtitle: bool = False,
    ) -> TorrentWithRelay:
        self._validate_file(torrent_file, file_index, require_subtitle)

        with isolated_db_session() as local_db:
            return create_torrents_service(local_db).create_from_torrent_file(
                torrent_file
            )

    def _validate_file(
        self,
        torrent_file: TorrentFileModel,
        file_index: int,
        require_subtitle: bool = False,
    ):
        if file_index not in range(len(torrent_file.info.files)):
            raise HTTPException(400, "Érvénytelen fájl index.")

        file_info = torrent_file.info.files[file_index]
        validate_file_type(
            is_video=file_info.is_video,
            is_subtitle=file_info.is_subtitle,
            require_subtitle=require_subtitle,
        )

    def _parse_range_header(
        self,
        file_size: int,
        range_header: str | None = None,
    ) -> ParsedRangeHeader:
        return parse_range_header(file_size=file_size, range_header=range_header)


def validate_file_type(
    is_video: bool,
    is_subtitle: bool,
    require_subtitle: bool = False,
) -> None:
    """Minden kérésre (új és már relayben lévő torrentnél is) azonos típusszabály."""
    if require_subtitle:
        if not is_subtitle:
            raise HTTPException(400, "A megadott fájl nem felirat.")
        return
    if not (is_video or is_subtitle):
        raise HTTPException(400, "A megadott fájl nem videó vagy felirat.")


def _range_not_satisfiable(file_size: int, detail: str) -> HTTPException:
    return HTTPException(
        416,
        detail,
        headers={"Content-Range": f"bytes */{file_size}"},
    )


def _parse_ascii_uint_capped(text: str, cap: int) -> int:
    if not text or not text.isascii() or not text.isdecimal():
        raise ValueError("Invalid ASCII decimal")
    digits = text.lstrip("0") or "0"
    ceiling = str(cap)
    if len(digits) > len(ceiling) or (len(digits) == len(ceiling) and digits > ceiling):
        return cap
    return int(digits)


def parse_range_header(
    file_size: int,
    range_header: str | None = None,
) -> ParsedRangeHeader:
    """HTTP Range (RFC 9110 14.1.2 / 14.2) feldolgozása egyetlen byte-tartományra.

    - Hiányzó fejléc: teljes fájl.
    - `bytes=a-b`: a végpont a fájlvégre vágódik (`b >= N` esetén `N-1`).
    - `bytes=a-`: a-tól a fájl végéig. `a >= N` nem kielégíthető (416).
    - `bytes=-n`: utolsó n bájt; `n == 0` nem kielégíthető (416).
    - Szintaktikailag hibás vagy többtartományos kérés: szabályozott 416
      (`Content-Range: bytes */N`), soha nem kezeletlen 500. Multipart nem támogatott.
    """
    if range_header is None:
        return ParsedRangeHeader(
            start_byte=0,
            end_byte=file_size - 1,
            content_length=file_size,
        )

    unit, sep, range_value = range_header.strip().partition("=")
    if not sep or unit.strip().lower() != "bytes":
        raise _range_not_satisfiable(file_size, "Érvénytelen range header.")

    range_value = range_value.strip()
    if "," in range_value:
        raise _range_not_satisfiable(file_size, "A több tartomány nem támogatott.")

    start_str, dash, end_str = range_value.partition("-")
    start_str, end_str = start_str.strip(), end_str.strip()
    if not dash or (not start_str and not end_str):
        raise _range_not_satisfiable(file_size, "Érvénytelen range header.")
    if file_size <= 0:
        raise _range_not_satisfiable(file_size, "A kért tartomány kívül esik a fájlon.")

    try:
        start_value = _parse_ascii_uint_capped(start_str, file_size) if start_str else None
        end_value = _parse_ascii_uint_capped(end_str, file_size if start_value is None else file_size - 1) if end_str else None
    except ValueError:
        raise _range_not_satisfiable(file_size, "Érvénytelen range header.") from None

    if not start_str:
        suffix_length = end_value or 0
        if suffix_length <= 0:
            raise _range_not_satisfiable(file_size, "A kért tartomány kívül esik a fájlon.")
        start_byte = max(file_size - suffix_length, 0)
        end_byte = file_size - 1
    else:
        assert start_value is not None
        start_byte = start_value
        end_byte = end_value if end_value is not None else file_size - 1
        if start_byte > end_byte:
            raise _range_not_satisfiable(file_size, "Érvénytelen range header.")
        if start_byte >= file_size:
            raise _range_not_satisfiable(file_size, "A kért tartomány kívül esik a fájlon.")
        end_byte = min(end_byte, file_size - 1)

    return ParsedRangeHeader(
        start_byte=start_byte,
        end_byte=end_byte,
        content_length=end_byte - start_byte + 1,
    )
