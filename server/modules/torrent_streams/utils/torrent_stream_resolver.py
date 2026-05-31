import re
import uuid

import content_types
import PTN
from common.torrent_info import TorrentFileInfo
from modules.attributes.models import AttributeModel
from modules.indexers.schemas import IndexerTorrent
from modules.stremio.schemas import ParsedStreamSeries
from modules.torrent_files.models import TorrentFileModel
from modules.torrent_streams.schemas import TorrentStream
from modules.torrent_streams.utils.metadata_parser import TorrentMetadataParser
from modules.users.models import UserModel


def is_video(filename: str) -> bool:
    content_type = content_types.get_content_type(filename)
    return bool(content_type and content_type.startswith("video/"))


def is_sample(name: str) -> bool:
    base = re.sub(r"\.[^.]+$", "", name.lower())
    return bool(re.search(r"(^sample|sample$|sample-|-sample-|-sample)", base))


def is_sample_or_trash(name: str) -> bool:
    if not is_video(name):
        return True
    return is_sample(name)


class TorrentStreamResolver:
    def __init__(
        self,
        indexer_torrent: IndexerTorrent,
        torrent_file: TorrentFileModel,
        series: ParsedStreamSeries | None,
        attribute_map: dict[str, AttributeModel],
        app_url: str,
        user: UserModel,
    ):
        self._indexer_torrent = indexer_torrent
        self._torrent_file = torrent_file
        self._series = series
        self._attribute_map = attribute_map
        self._app_url = app_url
        self._user = user

    def resolve(self) -> TorrentStream | None:
        if self._series:
            torrent_file = self.resolve_series_file(self._series)
        else:
            torrent_file = self._resolve_largest_file()

        if torrent_file is None:
            return None

        parse_attributes = TorrentMetadataParser(
            name=self._torrent_file.info.name,
            attributes_map=self._attribute_map,
            fallback_attributes=[],
        )

        parsed_attributes = parse_attributes.parse()

        indexer_id = self._indexer_torrent.indexer_account.indexer_id
        torrent_id = self._torrent_file.torrent_id
        file_index = torrent_file.index
        session_id = str(uuid.uuid4())

        return TorrentStream(
            indexer_account=self._indexer_torrent.indexer_account,
            torrent_id=torrent_id,
            info_hash=self._torrent_file.info_hash,
            seeders=self._indexer_torrent.seeders,
            torrent_name=self._torrent_file.info.name,
            attributes=parsed_attributes,
            file_name=torrent_file.name,
            file_size=torrent_file.size,
            file_index=file_index,
            play_url=f"{self._app_url}/api/{self._user.token}/stream/{indexer_id}/{torrent_id}/{file_index}/{session_id}",
            is_persisted_torrent=False,
        )

    def _resolve_largest_file(self) -> TorrentFileInfo | None:
        valid_files = [
            file
            for file in self._torrent_file.info.files
            if is_video(file.name) and not is_sample(file.name)
        ]
        if not valid_files:
            return None
        return max(valid_files, key=lambda file: file.size)

    def resolve_series_file(self, series: ParsedStreamSeries) -> TorrentFileInfo | None:
        for file in self._torrent_file.info.files:
            if is_sample_or_trash(file.name):
                continue

            parsed = PTN.parse(file.name)
            season = parsed.get("season")
            episode = parsed.get("episode")

            if season is None or episode is None:
                continue

            seasons = season if isinstance(season, list) else [season]
            episodes = episode if isinstance(episode, list) else [episode]

            if series.season in seasons and series.episode in episodes:
                return file

        return None
