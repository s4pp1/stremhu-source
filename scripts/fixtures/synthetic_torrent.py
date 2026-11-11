"""Synthetic single-file v1 torrents whose content is all zero bytes.

The piece hashes are the SHA-1 of zero-filled pieces, so any peer that sends
zeros (``local_bt_seed``) produces natively verified pieces.
"""

import hashlib
from dataclasses import dataclass


def _bencode(value) -> bytes:
    if isinstance(value, int):
        return b"i%de" % value
    if isinstance(value, bytes):
        return b"%d:%s" % (len(value), value)
    if isinstance(value, str):
        return _bencode(value.encode())
    if isinstance(value, dict):
        items = sorted((k.encode() if isinstance(k, str) else k, v) for k, v in value.items())
        return b"d" + b"".join(_bencode(k) + _bencode(v) for k, v in items) + b"e"
    raise TypeError(type(value).__name__)


@dataclass(frozen=True)
class SyntheticTorrent:
    name: str
    piece_size: int
    total_size: int
    info_hash: bytes
    torrent_bytes: bytes

    @property
    def piece_count(self) -> int:
        return (self.total_size + self.piece_size - 1) // self.piece_size


def build(name: str, piece_size: int, total_size: int, announce: str | None = None) -> SyntheticTorrent:
    if piece_size <= 0 or piece_size % 16384 or total_size <= 0:
        raise ValueError("Piece size must be a positive multiple of 16 KiB")
    full = hashlib.sha1(bytes(piece_size)).digest()
    count, last = divmod(total_size, piece_size)
    pieces = full * count + (hashlib.sha1(bytes(last)).digest() if last else b"")
    info = {"name": name, "piece length": piece_size, "length": total_size, "pieces": pieces, "private": 1}
    encoded_info = _bencode(info)
    metainfo = {"info": info}
    if announce:
        metainfo["announce"] = announce
    torrent_bytes = _bencode(metainfo)
    return SyntheticTorrent(name, piece_size, total_size, hashlib.sha1(encoded_info).digest(), torrent_bytes)
