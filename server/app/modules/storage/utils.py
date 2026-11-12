from collections.abc import Sequence

GIB = 1024 * 1024 * 1024

# Ennyi szabad helyet mindig tartalékolunk a futó letöltéseken felül.
MAX_RESERVE_BYTES = 5 * GIB
RESERVE_RATIO = 0.05


def reserve_bytes(capacity_bytes: int) -> int:
    """Biztonsági tartalék: a kapacitás 5%-a, de legfeljebb 5 GiB."""
    return min(MAX_RESERVE_BYTES, int(max(0, capacity_bytes) * RESERVE_RATIO))


def plan_eviction(
    free_bytes: int,
    required_free_bytes: int,
    candidates: Sequence[tuple[str, int]],
) -> list[str]:
    """Kiválasztja, mely torrenteket kell törölni a szükséges szabad helyhez.

    A `candidates` már prioritás szerint rendezett (legrégebben használt elöl),
    elemei `(info_hash, lemezen_foglalt_bájt)` párok. Csak annyit töröl, amennyi
    feltétlenül szükséges; ha a jelöltek összesen sem elegendőek, mindet törli.
    """
    if free_bytes >= required_free_bytes:
        return []

    selected: list[str] = []
    for info_hash, size in candidates:
        if free_bytes >= required_free_bytes:
            break
        selected.append(info_hash)
        free_bytes += max(0, size)

    return selected
