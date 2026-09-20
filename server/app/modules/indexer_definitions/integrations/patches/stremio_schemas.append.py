from app.modules.preferences.seeds import (  # noqa: E402
    DISCOUNT_PREFERENCE_ID as _STREMHU_DISCOUNT_PREFERENCE_ID,
)

_stremhu_original_from_imdb_torrent_stream = (
    StremioStream.from_imdb_torrent_stream.__func__
)


def _stremhu_from_imdb_torrent_stream(
    cls,
    torrent_stream: TorrentStream,
) -> StremioStream:
    stream = _stremhu_original_from_imdb_torrent_stream(cls, torrent_stream)

    # A teljes nevet írjuk ki (FreeLeech / Half-leech), nem a rövidítést: ez a
    # jelölés ritka, és a stream sorában egyértelműnek kell lennie.
    labels = [
        attribute.name or attribute.short_name
        for attribute in torrent_stream.attributes
        if getattr(attribute, "preference_id", None)
        == _STREMHU_DISCOUNT_PREFERENCE_ID
    ]

    if not labels:
        return stream

    emoji = EMOJI_MAP.get(_STREMHU_DISCOUNT_PREFERENCE_ID)
    badge = f"{emoji} {', '.join(labels)}" if emoji else ", ".join(labels)

    lines = stream.description.split("\n")
    lines[0] = " | ".join(compact([lines[0], badge]))
    stream.description = "\n".join(lines)

    return stream


StremioStream.from_imdb_torrent_stream = classmethod(
    _stremhu_from_imdb_torrent_stream
)
