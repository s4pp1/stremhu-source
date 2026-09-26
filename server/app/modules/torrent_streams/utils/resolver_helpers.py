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
