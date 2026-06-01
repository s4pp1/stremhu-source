import uuid

import PTN
from common.torrent_info import TorrentFileInfo, TorrentInfo
from modules.attributes.models import AttributeModel
from modules.indexer_accounts.models import IndexerAccountModel
from modules.indexers.schemas import IndexerTorrent
from modules.stremio.schemas import ParsedStreamSeries
from modules.torrent_files.models import TorrentFileModel
from modules.torrent_streams.utils.metadata_parser import TorrentMetadataParser
from modules.torrent_streams.utils.resolver_helpers import (
    is_sample,
    is_sample_or_trash,
    is_video,
)
from modules.users.models import UserModel
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class TorrentStream(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    indexer_account: IndexerAccountModel
    torrent_id: str
    info_hash: str
    torrent_name: str
    file_name: str
    file_size: int
    file_index: int
    play_url: str
    seeders: int | None = None
    attributes: list[AttributeModel] = []
    is_persisted_torrent: bool

    @classmethod
    def from_torrent_id_base(
        cls,
        indexer_torrent: IndexerTorrent,
        torrent_file: TorrentFileModel,
        app_url: str,
        user: UserModel,
    ) -> list["TorrentStream"]:
        return [
            cls(
                indexer_account=indexer_torrent.indexer_account,
                torrent_id=torrent_file.torrent_id,
                info_hash=torrent_file.info_hash,
                torrent_name=torrent_file.info.name,
                file_name=file.name,
                file_size=file.size,
                file_index=file.index,
                play_url=f"{app_url}/api/{user.token}/stream/{indexer_torrent.indexer_account.indexer_id}/{torrent_file.torrent_id}/{file.index}/{uuid.uuid4().hex}",
                seeders=indexer_torrent.seeders,
                attributes=[],
                is_persisted_torrent=False,
            )
            for file in torrent_file.info.files
            if file.is_video
        ]

    @classmethod
    def from_imdb_id_base(
        cls,
        indexer_torrent: IndexerTorrent,
        torrent_file: TorrentFileModel,
        attribute_map: dict[str, AttributeModel],
        app_url: str,
        user: UserModel,
        series: ParsedStreamSeries | None = None,
    ) -> "TorrentStream | None":
        if series:
            torrent_info = cls._resolve_series_file(
                torrent_file.info,
                series,
            )
        else:
            torrent_info = cls._resolve_largest_file(torrent_file.info)

        if torrent_info is None:
            return None

        parse_attributes = TorrentMetadataParser(
            name=torrent_info.name,
            attributes_map=attribute_map,
            fallback_attributes=[],
        )

        parsed_attributes = parse_attributes.parse()

        indexer_id = indexer_torrent.indexer_account.indexer_id
        torrent_id = torrent_file.torrent_id
        file_index = torrent_info.index
        session_id = uuid.uuid4().hex

        return TorrentStream(
            indexer_account=indexer_torrent.indexer_account,
            torrent_id=torrent_id,
            info_hash=torrent_file.info_hash,
            seeders=indexer_torrent.seeders,
            torrent_name=torrent_info.name,
            attributes=parsed_attributes,
            file_name=torrent_info.name,
            file_size=torrent_info.size,
            file_index=file_index,
            play_url=f"{app_url}/api/{user.token}/stream/{indexer_id}/{torrent_id}/{file_index}/{session_id}",
            is_persisted_torrent=False,
        )

    @staticmethod
    def _resolve_largest_file(torrent_info: TorrentInfo) -> TorrentFileInfo | None:
        valid_files = [
            file
            for file in torrent_info.files
            if is_video(file.name) and not is_sample(file.name)
        ]

        if not valid_files:
            return None

        return max(valid_files, key=lambda file: file.size)

    @staticmethod
    def _resolve_series_file(
        torrent_info: TorrentInfo,
        series: ParsedStreamSeries,
    ) -> TorrentFileInfo | None:
        for file in torrent_info.files:
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
