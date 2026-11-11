import html
import re
from dataclasses import dataclass, field


@dataclass
class TechInfoMetadata:
    audio_languages: set[str] = field(default_factory=set)
    has_hungarian_sub: bool = False


_RE_HTML_TAGS = re.compile(r"<[^>]+>")
_RE_HTML_BR = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)

# MediaInfo Section headers (pl. "Audio #1", "Hang #2", "Szöveg #1", "Text", "Felirat")
_RE_AUDIO_SECTION = re.compile(
    r"^\s*(?:Audio|Hang)(?:\s*#?\s*\d+)?\s*$", re.IGNORECASE
)
_RE_TEXT_SECTION = re.compile(
    r"^\s*(?:Text|Subtitle|Subtitles|Szöveg|Felirat)(?:\s*#?\s*\d+)?\s*$",
    re.IGNORECASE,
)
_RE_OTHER_SECTION = re.compile(
    r"^\s*(?:General|Általános|Video|Videó|Menu|Menü|Chapters|Fejezetek)(?:\s*#?\s*\d+)?\s*$",
    re.IGNORECASE,
)

# MediaInfo property matchers:
# Támogatja a MediaInfo "Language : Japanese", "Nyelv : magyar", valamint pontozott formátumokat: "Language.......: Japanese"
_RE_PROPERTY_LINE = re.compile(
    r"^\s*(?:(Language|Nyelv|Title|Cím)[\s\.:]+)(.*)$", re.IGNORECASE
)

# Description line matchers (pl. "Hangsáv: Japán 2.0", "Feliratok: Magyar")
_RE_DESC_AUDIO_LINE = re.compile(
    r"(?:^|\n)\s*(?:Hang(?:sáv)?|Audio)\s*[:=]\s*([^\r\n]+)", re.IGNORECASE
)
_RE_DESC_SUB_LINE = re.compile(
    r"(?:^|\n)\s*(?:Felirat(?:ok)?|Subtitles?|Subs?)\s*[:=]\s*([^\r\n]+)",
    re.IGNORECASE,
)

# Language tokens
_RE_JAP = re.compile(r"\b(jap(?:[-_. ]?dub)?|japanese|japán|jpn|ja)\b", re.IGNORECASE)
_RE_HUN = re.compile(r"\b(hun(?:[-_. ]?dub)?|hungarian|magyar|hu)\b", re.IGNORECASE)
_RE_ENG = re.compile(r"\b(eng(?:[-_. ]?dub)?|english|angol|en)\b", re.IGNORECASE)


def _detect_languages_in_text(text: str) -> set[str]:
    langs: set[str] = set()
    if _RE_JAP.search(text):
        langs.add("jap")
    if _RE_HUN.search(text):
        langs.add("hun")
    if _RE_ENG.search(text):
        langs.add("eng")
    return langs


def _clean_html(text: str) -> str:
    if not text:
        return ""
    # Sortörések megőrzése a <br> tagokból
    cleaned = _RE_HTML_BR.sub("\n", text)
    # Maradék HTML tagek eltávolítása
    cleaned = _RE_HTML_TAGS.sub(" ", cleaned)
    # Entitások feloldása (&amp;, &nbsp;, stb.)
    return html.unescape(cleaned)


def parse_tech_info_metadata(
    nfo_text: str = "",
    description_text: str = "",
) -> TechInfoMetadata:
    """
    Kinyeri a Tech Info (MediaInfo) és a torrent leírás szövegéből a valós
    hangsávokat és a magyar felirat meglétét.
    """
    meta = TechInfoMetadata()

    combined_sources = [
        _clean_html(nfo_text),
        _clean_html(description_text),
    ]

    for raw_text in combined_sources:
        if not raw_text:
            continue

        lines = raw_text.splitlines()
        current_section: str | None = None

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Szekcióváltások ellenőrzése
            if _RE_AUDIO_SECTION.match(stripped):
                current_section = "audio"
                continue
            if _RE_TEXT_SECTION.match(stripped):
                current_section = "text"
                continue
            if _RE_OTHER_SECTION.match(stripped):
                current_section = "other"
                continue

            # Ha a MediaInfo Audio/Hang szekciójában vagyunk
            if current_section == "audio":
                prop_match = _RE_PROPERTY_LINE.match(stripped)
                if prop_match:
                    prop_name = prop_match.group(1).lower()
                    prop_val = prop_match.group(2)
                    if prop_name in ("language", "nyelv", "title", "cím"):
                        meta.audio_languages.update(_detect_languages_in_text(prop_val))

            # Ha a MediaInfo Text/Szöveg/Felirat szekciójában vagyunk
            elif current_section == "text":
                prop_match = _RE_PROPERTY_LINE.match(stripped)
                if prop_match:
                    prop_name = prop_match.group(1).lower()
                    prop_val = prop_match.group(2)
                    if prop_name in ("language", "nyelv", "title", "cím"):
                        if _RE_HUN.search(prop_val):
                            meta.has_hungarian_sub = True

        # Szabadszavas leírások sorainak elemzése (pl. nCore torrent_drop leírás)
        for m in _RE_DESC_AUDIO_LINE.finditer(raw_text):
            meta.audio_languages.update(_detect_languages_in_text(m.group(1)))

        for m in _RE_DESC_SUB_LINE.finditer(raw_text):
            if _RE_HUN.search(m.group(1)):
                meta.has_hungarian_sub = True

    return meta

