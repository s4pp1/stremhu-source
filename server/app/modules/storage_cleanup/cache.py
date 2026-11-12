from collections.abc import Iterable

# Indexerenkénti Hit'n'Run függő torrent azonosítók. Hiányzó kulcs = ismeretlen állapot.
_hnr_pending_ids: dict[str, frozenset[str]] = {}


def get_hnr_pending_ids(indexer_id: str) -> frozenset[str] | None:
    return _hnr_pending_ids.get(indexer_id)


def set_hnr_pending_ids(indexer_id: str, torrent_ids: Iterable[str]) -> None:
    _hnr_pending_ids[indexer_id] = frozenset(torrent_ids)


def clear_hnr_pending_ids(indexer_id: str) -> None:
    _hnr_pending_ids.pop(indexer_id, None)
