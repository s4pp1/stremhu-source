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


def is_sample(name: str) -> bool:
    base = re.sub(r"\.[^.]+$", "", name.lower())
    return bool(re.search(r"(^sample|sample$|sample-|-sample-|-sample)", base))


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
    r"creditless"
    r")(?:[ ._\]\)-]|\.[^.]+$)",
    re.IGNORECASE,
)

# A „menu” és a „sample” cím- és epizódcímszó is lehet (pl. The Menu), ezért csak
# a fájlnév utolsó szavaként jelöl extrát, és explicit SxxEyy jelölés mellett soha.
MENU_OR_SAMPLE_FILE_REGEX = re.compile(
    r"(?:^|[ ._\[\(-])(?:men[uü]|sample)(?:[ ._-]?\d{1,2})?[ \]\)]*\.[^.]+$",
    re.IGNORECASE,
)
EXPLICIT_EPISODE_REGEX = re.compile(
    r"(?:^|[^a-z0-9])s\d{1,2}[ ._-]?e\d{1,4}(?![0-9])",
    re.IGNORECASE,
)


def is_extra_file(filename: str) -> bool:
    if EXTRA_FILE_REGEX.search(filename):
        return True
    return bool(MENU_OR_SAMPLE_FILE_REGEX.search(filename)) and not bool(
        EXPLICIT_EPISODE_REGEX.search(filename)
    )
