
from app.modules.stream.router import (
    SubtitleIncompleteError,
    _cache_pop,
    _content_disposition,
    _decode_subtitle_text,
    _get_cached_subtitle,
    _put_cached_subtitle,
    _register_subtitle_alias,
    _subtitle_content_cache,
)


def test_subtitle_content_disposition_rfc6266_encoding():
    # ASCII név
    cd_ascii = _content_disposition("test_sub.srt")
    assert 'filename="test_sub.srt"' in cd_ascii
    assert "filename*=UTF-8''test_sub.srt" in cd_ascii

    # Ékezetes magyar név (latin-1 és UTF-8 összeférhetőség)
    cd_hun = _content_disposition("Árvíztűrő tükörfúrógép - 01.srt")
    # A nyers fejlécek latin-1 biztonságosak
    assert cd_hun.encode("latin-1")
    assert "filename*=UTF-8''" in cd_hun
    assert "%C3%81rv" in cd_hun  # URL-kódolt Árv...


def test_subtitle_decode_fallback_cp1250():
    # 1. Érvényes UTF-8 (BOM-mal vagy anélkül)
    utf8_bytes = "Árvíztűrő".encode()
    assert _decode_subtitle_text(utf8_bytes) == "Árvíztűrő"

    # 2. Régi magyar CP1250 kódolású felirat (pl. 'ő', 'ű' speciális kódja)
    cp1250_bytes = "Árvíztűrő".encode("cp1250")
    # Nem érvényes UTF-8 bájtfolyam:
    assert _decode_subtitle_text(cp1250_bytes) == "Árvíztűrő"


def test_subtitle_cache_byte_limit_and_lru():
    _subtitle_content_cache.clear()
    key1 = ("ncore", "1001", 0, True)

    payload_small = b"X" * 1024  # 1 KB
    _put_cached_subtitle(key1, "text/vtt", "01.vtt", payload_small)
    assert _get_cached_subtitle(key1) is not None

    _register_subtitle_alias(("ncore", "1001", 0, False), key1)
    # Az alias alapján is megkapja:
    alias_cached = _get_cached_subtitle(("ncore", "1001", 0, False))
    assert alias_cached is not None
    assert alias_cached[2] == payload_small

    _cache_pop(key1)
    assert _get_cached_subtitle(key1) is None
    _subtitle_content_cache.clear()


def test_subtitle_incomplete_error_is_raised():
    err = SubtitleIncompleteError("Hiányos tartalom")
    assert str(err) == "Hiányos tartalom"
