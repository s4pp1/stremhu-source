import datetime
import hashlib
import json
import typing
from pathlib import Path

import libtorrent
import pydash

from app.common.torrent_info import TorrentFileInfo, TorrentInfo
from app.modules.indexer_accounts.models import IndexerAccountModel
from app.modules.indexer_definitions.models import IndexerDefinitionModel
from app.modules.indexers.schemas.internal import IndexerTorrent
from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.media_attributes.seeds import DEFAULT_ATTRIBUTES
from app.modules.torrent_files.models import TorrentFileModel
from app.modules.torrent_source_provider.schemas import TorrentSource


def create_torrent_file_info(
    path: str,
    size: int,
    is_video: bool = True,
    index: int = 0,
) -> TorrentFileInfo:
    return TorrentFileInfo(
        name=path.split("/")[-1],
        path=path,
        index=index,
        size=size,
        offset=0,
        start_piece_index=0,
        end_piece_index=0,
        is_video=is_video,
    )


def create_torrent_info(
    name: str,
    files: list[TorrentFileInfo],
    info_hash: str = "hash",
    size: int | None = None,
    piece_size: int = 10,
) -> TorrentInfo:
    if size is None:
        size = sum(f.size for f in files)

    return TorrentInfo(
        info_hash=info_hash,
        name=name,
        size=size,
        piece_size=piece_size,
        files=files,
    )


def get_attributes_by_ids(ids: list[str]) -> list[MediaAttributeModel]:
    mapping = {attr.id: attr for attr in DEFAULT_ATTRIBUTES}
    return [mapping[id_] for id_ in ids if id_ in mapping]


class StreamFileDict(typing.TypedDict):
    path: str
    size: int
    is_video: bool


class StreamTorrentDict(typing.TypedDict):
    name: str
    files: list[StreamFileDict]


class StreamQueryDict(typing.TypedDict):
    series: dict[str, typing.Any] | None
    expected_file: str


class StreamTestCaseDict(typing.TypedDict):
    external_fallbacks: list[str]
    torrent: StreamTorrentDict
    queries: list[StreamQueryDict]


def load_streams_from_json(file_name: str = "streams.json") -> dict[str, typing.Any]:
    json_path = Path(__file__).parent / "data" / file_name
    with open(json_path, encoding="utf-8") as f:
        data = typing.cast(dict[str, StreamTestCaseDict], json.load(f))

    parsed_data: dict[str, typing.Any] = {}

    for key, value in data.items():
        torrent_data = value["torrent"]
        files = [
            create_torrent_file_info(
                path=file["path"],
                size=file["size"],
                is_video=file["is_video"],
                index=i,
            )
            for i, file in enumerate(torrent_data["files"])
        ]
        torrent_info = create_torrent_info(
            name=torrent_data["name"],
            files=files,
        )

        external_fallbacks = get_attributes_by_ids(
            typing.cast(list[str], pydash.get(value, "external_fallbacks", []))
        )

        parsed_data[key] = {
            "torrent_info": torrent_info,
            "queries": typing.cast(
                list[StreamQueryDict], pydash.get(value, "queries", [])
            ),
            "external_fallbacks": external_fallbacks,
        }

    return parsed_data


def create_torrent_source(
    indexer_id: str,
    indexer_name: str,
    torrent_id: str,
    name: str,
    files: list[str] | None = None,
    file_size: int = 50_000,
    seeders: int = 0,
    imdb_id: str | None = None,
    attribute_ids: list[str] | None = None,
) -> TorrentSource:
    file_names = files if files is not None else [name]
    torrent_files = [
        create_torrent_file_info(
            path=f"{name}/{file_name}" if files is not None else file_name,
            size=file_size,
            index=index,
        )
        for index, file_name in enumerate(file_names)
    ]

    definition = IndexerDefinitionModel(
        id=indexer_id,
        name=indexer_name,
        url=f"https://{indexer_id}.invalid",
        details_path="/details",
    )
    account = IndexerAccountModel(
        indexer_id=indexer_id,
        username="teszt",
        password="teszt",
    )
    account.indexer_definition = definition

    torrent_bytes = libtorrent.bencode(
        {
            b"info": {
                b"name": b"x",
                b"piece length": 16384,
                b"pieces": b"\0" * 20,
                b"length": 1,
            }
        }
    )

    torrent_file = TorrentFileModel(
        indexer_id=indexer_id,
        torrent_id=torrent_id,
        torrent_bytes=torrent_bytes,
    )
    torrent_file._cached_info = create_torrent_info(
        name=name,
        files=torrent_files,
        info_hash=hashlib.sha1(f"{indexer_id}:{torrent_id}".encode()).hexdigest(),
    )
    # Időzóna nélkül a formázó a gép helyi idejét feltételezné,
    # és a snapshot gépenként más lenne.
    torrent_file.created_at = datetime.datetime(
        2026, 3, 4, 17, 5, 9, tzinfo=datetime.UTC
    )

    return TorrentSource(
        indexer_torrent=IndexerTorrent(
            indexer_account=account,
            torrent_id=torrent_id,
            download_url=f"https://{indexer_id}.invalid/dl/{torrent_id}",
            imdb_id=imdb_id,
            seeders=seeders,
            media_attributes=get_attributes_by_ids(attribute_ids or []),
        ),
        torrent_file=torrent_file,
    )
