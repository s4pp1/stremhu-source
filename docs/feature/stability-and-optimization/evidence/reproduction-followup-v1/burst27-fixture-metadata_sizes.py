"""Deterministic synthetic .torrent sizes for G15 fixture preparation.

Metadata is parsed by the pinned native codec. Piece hashes describe synthetic
metadata only: no payload files, sessions, trackers or downloads are created.
One parse per profile validates wiring/size, not a performance acceptance gate.
"""

import gc
import hashlib
import json

import libtorrent


PROFILES = [
    (1 << 30, 256 << 10, 1),
    (16 << 30, 1 << 20, 100),
    (256 << 30, 4 << 20, 1000),
    (1 << 40, 1 << 20, 10000),
    (1 << 40, 4 << 20, 50000),
    (1 << 40, 256 << 10, 10000),
]


def make_metadata(total_size: int, piece_size: int, file_count: int) -> bytes:
    if not 1 <= file_count <= 50000 or total_size < file_count:
        raise ValueError("Synthetic file count outside bounded fixture")
    piece_count = (total_size + piece_size - 1) // piece_size
    if piece_count > 4194304:
        raise ValueError("Synthetic piece count outside bounded fixture")
    length, remainder = divmod(total_size, file_count)
    files = [{b"length": length + (index < remainder),
              b"path": [f"synthetic-{index:06d}.mkv".encode()]}
             for index in range(file_count)]
    info = {b"name": b"synthetic-metadata-only", b"piece length": piece_size,
            b"pieces": hashlib.sha1(b"synthetic metadata only").digest() * piece_count,
            b"files": files, b"private": 1}
    return libtorrent.bencode({b"info": info})


def main():
    rows = []
    for total, piece_size, files in PROFILES:
        body = make_metadata(total, piece_size, files)
        row = dict(logical_payload_bytes=total, piece_size=piece_size,
                   files=files, piece_count=(total + piece_size - 1) // piece_size,
                   metadata_bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        try:
            parsed = libtorrent.torrent_info(body)
            if parsed.total_size() != total or parsed.num_files() != files:
                raise AssertionError("Native metadata interpretation differs")
            row["native_state"] = "accepted"
            del parsed
        except RuntimeError as error:
            row.update(native_state="rejected", exception_kind=type(error).__name__)
        rows.append(row)
        del body
        gc.collect()
    print(json.dumps(dict(fixture="g15-native-torrent-metadata-size-wiring-v1",
                          is_measurement=False, native_version=libtorrent.version,
                          rows=rows, payload_verified=False,
                          scope="Synthetic deterministic metadata, actual native parsing only; no HTTP/origin/auth/admission test or production size-policy decision.")))


if __name__ == "__main__":
    main()
