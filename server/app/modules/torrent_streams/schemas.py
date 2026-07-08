import uuid

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.common.schemas.internal import SeriesInfo
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.indexers.schemas.internal import IndexerTorrent
from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.media_attributes.parser import parse_torrent_name
from app.modules.stream.schemas import StreamToken
from app.modules.stream.utils.stream_token import generate_stream_token
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_streams.utils.resolver_helpers import is_sample_or_trash
from app.modules.torrent_streams.utils.stream_file_resolver import StreamFileResolver
from app.modules.users.models import UserModel


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
    attributes: list[MediaAttributeModel | IndexerDefinitionModel] = []
    is_persisted_torrent: bool

    @classmethod
    def from_torrent_id(
        cls,
        indexer_torrent: IndexerTorrent,
        torrent_file: TorrentFileModel,
        app_url: str,
        user: UserModel,
    ) -> list["TorrentStream"]:
        indexer_id = indexer_torrent.indexer_account.indexer_id

        torrent_streams: list[TorrentStream] = []

        for file in torrent_file.info.files:
            if not file.is_video:
                continue

            if is_sample_or_trash(file.name):
                continue

            stream_token = generate_stream_token(
                StreamToken(
                    indexer_id=indexer_id,
                    torrent_id=torrent_file.torrent_id,
                    file_index=file.index,
                    playback_id=str(uuid.uuid4()),
                )
            )

            torrent_streams.append(
                cls(
                    indexer_account=indexer_torrent.indexer_account,
                    torrent_id=torrent_file.torrent_id,
                    info_hash=torrent_file.info_hash,
                    torrent_name=torrent_file.info.name,
                    file_name=file.name,
                    file_size=file.size,
                    file_index=file.index,
                    play_url=f"{app_url}/api/{user.api_key}/stream/{stream_token}",
                    seeders=indexer_torrent.seeders,
                    attributes=[],
                    is_persisted_torrent=False,
                )
            )

        return torrent_streams

    @classmethod
    def from_imdb_id(
        cls,
        indexer_torrent: IndexerTorrent,
        torrent_file: TorrentFileModel,
        app_url: str,
        user: UserModel,
        series: SeriesInfo | None = None,
    ) -> "TorrentStream | None":
        torrent_file_info = StreamFileResolver.resolve_file(
            torrent_file.info,
            series,
        )

        if torrent_file_info is None:
            return None

        torrent_attributes = parse_torrent_name(
            name=torrent_file.info.name,
            external_fallbacks=indexer_torrent.media_attributes,
        )

        file_attributes = parse_torrent_name(
            name=torrent_file_info.name,
            use_fallbacks=False,
        )

        torrent_attr_ids = {attribute.id for attribute in torrent_attributes}
        file_attr_ids = {attribute.id for attribute in file_attributes}

        if not file_attributes:
            parsed_attributes = torrent_attributes
        elif file_attr_ids == torrent_attr_ids:
            parsed_attributes = torrent_attributes
        else:
            # Intelligens összefésülés: a fájl attribútumai felülírják a torrent azonos kategóriájú (preference_id) attribútumait
            parsed_attributes = []
            file_pref_ids = {
                file_attribute.preference_id
                for file_attribute in file_attributes
                if file_attribute.preference_id is not None
            }

            for attr in torrent_attributes:
                # Ha a fájl tartalmaz attribútumot ebből a kategóriából, akkor a torrent-szintűt eldobjuk (felülíródik)
                if (
                    attr.preference_id is not None
                    and attr.preference_id in file_pref_ids
                ):
                    continue
                # Ha nincs kategória, de a fájl már pont tartalmazza ezt az attribútumot, akkor elkerüljük a duplikációt
                if attr.id in file_attr_ids:
                    continue
                parsed_attributes.append(attr)

            # Hozzáadjuk a fájl saját attribútumait
            parsed_attributes.extend(file_attributes)

        indexer_id = indexer_torrent.indexer_account.indexer_id
        torrent_id = torrent_file.torrent_id
        file_index = torrent_file_info.index
        playback_id = str(uuid.uuid4())

        stream_token = generate_stream_token(
            StreamToken(
                indexer_id=indexer_id,
                torrent_id=torrent_id,
                file_index=file_index,
                playback_id=playback_id,
                imdb_id=indexer_torrent.imdb_id,
                series_info=series,
            )
        )

        return TorrentStream(
            indexer_account=indexer_torrent.indexer_account,
            torrent_id=torrent_id,
            info_hash=torrent_file.info_hash,
            seeders=indexer_torrent.seeders,
            torrent_name=torrent_file.info.name,
            attributes=[
                *parsed_attributes,
                indexer_torrent.indexer_account.indexer_definition,
            ],
            file_name=torrent_file_info.name,
            file_size=torrent_file_info.size,
            file_index=file_index,
            play_url=f"{app_url}/api/{user.api_key}/stream/{stream_token}",
            is_persisted_torrent=False,
        )
