import libtorrent as libtorrent
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class RelaySettingsUpdate(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    download_limit: int | None = None
    upload_limit: int | None = None
    port: int | None = None
    connections_limit: int | None = None
    torrent_connections_limit: int | None = None
    enable_upnp_and_natpmp: bool | None = None


class RelayTorrentUpdate(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    priority: int | None = None


class RelayTorrent(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )

    name: str
    info_hash: str
    download_speed: int
    upload_speed: int
    downloaded: int
    uploaded: int
    total: int
    max_connections: int
    connections: int

    @classmethod
    def from_libtorrent_handle(cls, torrent_handle: libtorrent.torrent_handle):
        status = torrent_handle.status()

        total = 0
        torrent_info = torrent_handle.torrent_file()
        if torrent_info:
            total = torrent_info.total_size()

        return cls(
            name=status.name,
            info_hash=str(status.info_hash),
            download_speed=status.download_payload_rate,
            upload_speed=status.upload_payload_rate,
            downloaded=status.total_done,
            uploaded=status.all_time_upload,
            total=total,
            max_connections=status.connections_limit,
            connections=status.num_connections,
        )


class PieceOrFileAvailable(BaseModel):
    piece_available: bool
    file_available: bool
