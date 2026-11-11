import re

import content_types


def sanitize_filename_for_content_type(filename: str) -> str:
    """
    Replaces characters in the filename that could be misinterpreted by the
    content_types module's built-in URL parsing logic (like URL fragments or query params).
    """
    unsafe_chars = ["#", "?", " "]
    safe_filename = filename
    for char in unsafe_chars:
        safe_filename = safe_filename.replace(char, "_")
    return safe_filename


def is_video(filename: str) -> bool:
    safe_filename = sanitize_filename_for_content_type(filename)
    content_type = content_types.get_content_type(safe_filename)
    return bool(content_type and content_type.startswith("video/"))


SAMPLE_REGEX = re.compile(r"(^sample|sample$|sample-|-sample-|-sample|\bmen[uü]\b)")


def is_sample(name: str) -> bool:
    base = name.rsplit(".", 1)[0].lower()
    return bool(SAMPLE_REGEX.search(base))


def is_sample_or_trash(name: str) -> bool:
    if not is_video(name):
        return True
    return is_sample(name)


EXTRA_FOLDER_REGEX = re.compile(
    r"^(?:\d{1,2}[ ._-]+)?(?:"
    r"extras?|extrák|specials?|különkiadás(?:ok)?|bonus(?:es)?|bónusz(?:ok)?|"
    r"featurettes?|kisfilmek?|behind[ ._-]?the[ ._-]?scenes|deleted[ ._-]?scenes|"
    r"trailers?|előzetes(?:ek)?|scans?|borítók?|art(?:works?)?|soundtracks?|music|zene|ost|"
    r"nc(?:ed|op)\d*|creditless|oped\d*|samples?|minta|"
    r"(?:bd[ ._-]?|dvd[ ._-]?)?men[uü]|sp|oav|oad|ova"
    r")$"
    r"|^(?:s\d{1,2}|season[ ._-]?\d{1,2})[ ._-]+(?:extras?|extrák|specials?|különkiadás(?:ok)?|bonus(?:es)?|bónusz(?:ok)?)$"
    r"|^(?:extras?|extrák|specials?|különkiadás(?:ok)?|bonus(?:es)?|bónusz(?:ok)?)[ ._-]+(?:s\d{1,2}|season[ ._-]?\d{1,2})$",
    re.IGNORECASE,
)


def is_extra_folder(folder_name: str) -> bool:
    clean = folder_name.strip(" [](){}_-")
    return bool(EXTRA_FOLDER_REGEX.match(clean))


EXTRA_FILE_REGEX = re.compile(
    r"(?:^|[ ._\[\(-])(?:"
    r"extra[s]?[ ._\-]?\d+|"
    r"sp[ ._\-]?\d+|"
    r"special[s]?[ ._\-]?\d+|"
    r"o[av]a[ ._\-]?\d+|"
    r"oad[ ._\-]?\d+|"
    r"nc(?:ed|op)\d*|"
    r"creditless|"
    r"men[uü]|"
    r"sample"
    r")(?:[ ._\]\)-]|\.[^.]+$)",
    re.IGNORECASE,
)


def is_extra_file(filename: str) -> bool:
    return bool(EXTRA_FILE_REGEX.search(filename))


HUN_LANG_PATTERN = re.compile(
    r"(?:\b|[._\-\[])(?:hun|hu|hungarian|magyar|hunsub)(?:\b|[._\-\]])"
)

FOREIGN_LANG_PATTERNS = [
    (re.compile(r"(?:\b|[._\-\[])(?:eng|english|engsub)(?:\b|[._\-\]])|[._\-\[]en[._\-\]]"), "eng", "English"),
    (re.compile(r"(?:\b|[._\-\[])(?:ger|german|deutsch)(?:\b|[._\-\]])|[._\-\[]de[._\-\]]"), "ger", "German"),
    (re.compile(r"(?:\b|[._\-\[])(?:fre|fra|french|francais)(?:\b|[._\-\]])|[._\-\[]fr[._\-\]]"), "fre", "French"),
    (re.compile(r"(?:\b|[._\-\[])(?:spa|spanish|espanol)(?:\b|[._\-\]])|[._\-\[]es[._\-\]]"), "spa", "Spanish"),
    (re.compile(r"(?:\b|[._\-\[])(?:ita|italian|italiano)(?:\b|[._\-\]])|[._\-\[]it[._\-\]]"), "ita", "Italian"),
    (re.compile(r"(?:\b|[._\-\[])(?:rus|russian)(?:\b|[._\-\]])|[._\-\[]ru[._\-\]]"), "rus", "Russian"),
    (re.compile(r"(?:\b|[._\-\[])(?:jpn|jap|japanese)(?:\b|[._\-\]])|[._\-\[]ja[._\-\]]"), "jpn", "Japanese"),
    (re.compile(r"(?:\b|[._\-\[])(?:por|portuguese)(?:\b|[._\-\]])|[._\-\[]pt[._\-\]]"), "por", "Portuguese"),
    (re.compile(r"(?:\b|[._\-\[])(?:pol|polish)(?:\b|[._\-\]])|[._\-\[]pl[._\-\]]"), "pol", "Polish"),
    (re.compile(r"(?:\b|[._\-\[])(?:cze|ces|czech)(?:\b|[._\-\]])|[._\-\[]cz[._\-\]]"), "cze", "Czech"),
    (re.compile(r"(?:\b|[._\-\[])(?:chi|zho|chinese)(?:\b|[._\-\]])|[._\-\[]zh[._\-\]]"), "chi", "Chinese"),
    (re.compile(r"(?:\b|[._\-\[])(?:rom|romanian)(?:\b|[._\-\]])|[._\-\[]ro[._\-\]]"), "rom", "Romanian"),
]


def detect_subtitle_language(filename: str, path: str = "") -> tuple[str, str]:
    """
    Detects language code (ISO 639-2) and readable label from subtitle file name and path.
    Evaluates filename first to avoid false positives from folder release names (e.g. Movie.HUN.1080p/Subs/English.srt).
    Defaults to Hungarian ('hun', 'Hungarian (Torrent)') in context of Hungarian trackers/anime.
    """
    fn_lower = filename.lower()
    path_lower = path.lower()
    is_forced = "forced" in fn_lower or "forced" in path_lower

    # 1. lépés: Elsődlegesen a közvetlen fájlnevet vizsgáljuk
    if HUN_LANG_PATTERN.search(fn_lower):
        if is_forced:
            return "hun", "Hungarian (Forced)"
        return "hun", "Hungarian"

    for pattern, code, name in FOREIGN_LANG_PATTERNS:
        if pattern.search(fn_lower):
            if is_forced:
                return code, f"{name} (Forced)"
            return code, name

    # 2. lépés: Ha a fájlnév nem hordoz nyelvi kódot (pl. 01.srt), a szülőmappákat vizsgáljuk legbelülről kifelé
    clean_path = path.replace("\\", "/").strip("/")
    path_parts = [p for p in clean_path.split("/") if p]
    if path_parts and path_parts[-1].lower() == fn_lower:
        path_parts.pop()
    for folder in reversed(path_parts):
        folder_lower = folder.lower()
        if HUN_LANG_PATTERN.search(folder_lower):
            if is_forced:
                return "hun", "Hungarian (Forced)"
            return "hun", "Hungarian"
        for pattern, code, name in FOREIGN_LANG_PATTERNS:
            if pattern.search(folder_lower):
                if is_forced:
                    return code, f"{name} (Forced)"
                return code, name

    # 3. lépés: Ha a szülőmappákban sincs konkrét nyelvi almappa, de a teljes útvonal (pl. torrent cím) magyar jelölést tartalmaz (pl. [HunSub])
    if HUN_LANG_PATTERN.search(path_lower):
        if is_forced:
            return "hun", "Hungarian (Forced)"
        return "hun", "Hungarian"

    # 4. lépés: Alapértelmezés (magyar trackerek kontextusában)
    if is_forced:
        return "hun", "Hungarian (Torrent) (Forced)"
    return "hun", "Hungarian (Torrent)"
