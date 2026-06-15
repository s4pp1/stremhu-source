import re

import content_types


def is_video(filename: str) -> bool:
    content_type = content_types.get_content_type(filename)
    return bool(content_type and content_type.startswith("video/"))


def is_sample(name: str) -> bool:
    base = re.sub(r"\.[^.]+$", "", name.lower())
    return bool(re.search(r"(^sample|sample$|sample-|-sample-|-sample)", base))


def is_sample_or_trash(name: str) -> bool:
    if not is_video(name):
        return True
    return is_sample(name)
