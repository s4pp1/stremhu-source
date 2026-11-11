import asyncio
import codecs
import re

_STYLE_TAG_REGEX = re.compile(r"\{.*?\}")
_DRAWING_TAG_REGEX = re.compile(r"\{\\p[1-9]")
# Kooperatív feldolgozás szeletméretei: ennyi munka után visszaadja a vezérlést
# az event loopnak (dekódolás bájtban, konverzió karakterben).
_DECODE_BYTES_PER_SLICE = 256 * 1024
_CHARS_PER_SLICE = 32 * 1024


def decode_subtitle_text(raw_bytes: bytes) -> str:
    """Explicit dekódolási szabály: UTF-8 (BOM-mal vagy anélkül), ha érvényes;
    különben Windows-1250 (közép-európai, a magyar feliratok tipikus régi kódolása)."""
    try:
        return raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw_bytes.decode("cp1250", errors="replace")


async def _decode_in_slices(raw_bytes: bytes, encoding: str, errors: str) -> str:
    decoder = codecs.getincrementaldecoder(encoding)(errors=errors)
    parts: list[str] = []
    for start in range(0, len(raw_bytes), _DECODE_BYTES_PER_SLICE):
        end = start + _DECODE_BYTES_PER_SLICE
        parts.append(decoder.decode(raw_bytes[start:end], final=end >= len(raw_bytes)))
        await asyncio.sleep(0)
    parts.append(decoder.decode(b"", final=True))
    return "".join(parts)


async def decode_subtitle_text_cooperative(raw_bytes: bytes) -> str:
    """A ``decode_subtitle_text`` szabálya szeletenkénti dekódolással (azonos eredmény)."""
    try:
        return await _decode_in_slices(raw_bytes, "utf-8-sig", "strict")
    except UnicodeDecodeError:
        return await _decode_in_slices(raw_bytes, "cp1250", "replace")


def _format_ts(ts: str) -> str:
    p = ts.split(":")
    if len(p) < 3:
        return ts
    h = p[0].zfill(2)
    m = p[1].zfill(2)
    s = p[2]
    if "." in s:
        parts_s = s.split(".", 1)
        sec = parts_s[0].zfill(2)
        ms = parts_s[1].ljust(3, "0")[:3]
        return f"{h}:{m}:{sec}.{ms}"
    return f"{h}:{m}:{s.zfill(2)}.000"


class _AssToVttConverter:
    """Soronként feldolgozó ASS→VTT állapotgép; a szakaszállapot a hívások között megmarad."""

    def __init__(self) -> None:
        self._lines = ["WEBVTT\n"]
        self._in_events = False

    def feed(self, lines: list[str]) -> None:
        for line in lines:
            clean_line = line.strip()
            if clean_line.startswith("[") and clean_line.endswith("]"):
                self._in_events = clean_line.lower() == "[events]"
                continue
            if not self._in_events:
                continue
            if clean_line.startswith(("Dialogue:", "dialogue:")):
                parts = clean_line.split(",", 9)
                if len(parts) >= 10:
                    text = parts[9]
                    # Rajzolt alakzatok (vektor rajzok, pl. {\p1}m 0 0...{\p0}) kizárása
                    if _DRAWING_TAG_REGEX.search(text):
                        continue

                    start = parts[1].strip()
                    end = parts[2].strip()

                    # Stílus címkék törlése (pl. {\pos(100,200)}, {\c&H0000FF&})
                    text = _STYLE_TAG_REGEX.sub("", text)
                    # Sortörések és nem törő szóközök (\h) normalizálása
                    text = (
                        text.replace(r"\h", " ")
                        .replace(r"\N", "\n")
                        .replace(r"\n", "\n")
                        .strip()
                    )

                    if text:
                        self._lines.append(
                            f"{_format_ts(start)} --> {_format_ts(end)}\n{text}\n"
                        )

    def result(self) -> str:
        return "\n".join(self._lines)


def ass_to_vtt(content: str) -> str:
    """Konvertálja a SubStation Alpha (.ass / .ssa) szöveges feliratot WebVTT (.vtt) formátumra."""
    converter = _AssToVttConverter()
    converter.feed(content.splitlines())
    return converter.result()


async def ass_to_vtt_cooperative(
    content: str, chars_per_slice: int = _CHARS_PER_SLICE
) -> str:
    """Az ``ass_to_vtt``-vel azonos kimenet, de szeletenként visszaadja a vezérlést.

    Nagy (több MB-os) feliratnál így az event loop a konverzió alatt is kiszolgál
    más kéréseket; szál vagy külön processz nem kell hozzá. A szeletek mindig
    ``\\n`` után végződnek: ez egyetlen kétkarakteres sorvég (``\\r\\n``) második
    fele sem lehet, így a szeletenkénti ``splitlines`` a teljes szövegével azonos.
    """
    converter = _AssToVttConverter()
    pos, size = 0, len(content)
    while pos < size:
        cut = content.find("\n", pos + chars_per_slice - 1)
        end = size if cut == -1 else cut + 1
        converter.feed(content[pos:end].splitlines())
        pos = end
        await asyncio.sleep(0)
    return converter.result()
