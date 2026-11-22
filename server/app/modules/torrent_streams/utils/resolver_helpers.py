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
