import re
from collections import defaultdict
from typing import TypeAlias

from app.modules.media_attributes.models import MediaAttributeModel
from app.modules.media_attributes.seeds import DEFAULT_ATTRIBUTES
from app.modules.preferences.seeds import DEFAULT_PREFERENCES

PreferenceMultipleMap: TypeAlias = dict[str, bool]
PatternAttributeTuple: TypeAlias = tuple[re.Pattern[str], MediaAttributeModel]
GroupedAttributes: TypeAlias = dict[str | None, list[PatternAttributeTuple]]
FallbackAttributes: TypeAlias = dict[str | None, MediaAttributeModel]


_PREFERENCE_MULTIPLE_MAP: dict[str, bool] = {
    pref.id: pref.multiple for pref in DEFAULT_PREFERENCES
}

_GROUPED_ATTRIBUTES: GroupedAttributes = defaultdict(list)
_FALLBACKS: FallbackAttributes = {}

for attribute in DEFAULT_ATTRIBUTES:
    if isinstance(attribute.pattern, str):
        pattern = re.compile(attribute.pattern, re.IGNORECASE)
        _GROUPED_ATTRIBUTES[attribute.preference_id].append((pattern, attribute))
    else:
        _FALLBACKS[attribute.preference_id] = attribute


def parse_torrent_name(
    name: str,
    external_fallbacks: list[MediaAttributeModel] | None = None,
    use_fallbacks: bool = True,
) -> list[MediaAttributeModel]:
    name_lower = name.lower()
    matched_attributes: list[MediaAttributeModel] = []

    external_fallback_map: dict[str | None, MediaAttributeModel] = {}
    if external_fallbacks:
        for attr in external_fallbacks:
            external_fallback_map[attr.preference_id] = attr

    all_pref_ids = list(_GROUPED_ATTRIBUTES.keys())
    for pref_id in _FALLBACKS.keys():
        if pref_id not in all_pref_ids:
            all_pref_ids.append(pref_id)

    for pref_id in all_pref_ids:
        category_matched = False
        is_multiple = _PREFERENCE_MULTIPLE_MAP.get(pref_id, False) if pref_id else True

        for pattern, attr in _GROUPED_ATTRIBUTES.get(pref_id, []):
            if pattern.search(name_lower):
                matched_attributes.append(attr)
                category_matched = True

                if not is_multiple:
                    break

        if not category_matched and use_fallbacks:
            if pref_id in external_fallback_map:
                matched_attributes.append(external_fallback_map[pref_id])
            elif pref_id in _FALLBACKS:
                matched_attributes.append(_FALLBACKS[pref_id])

    return matched_attributes


def clean_torrent_name(name: str) -> str:
    name_cleaned = name
    all_pref_ids = list(_GROUPED_ATTRIBUTES.keys())
    for pref_id in _FALLBACKS.keys():
        if pref_id not in all_pref_ids:
            all_pref_ids.append(pref_id)

    for pref_id in all_pref_ids:
        for pattern, _ in _GROUPED_ATTRIBUTES.get(pref_id, []):
            name_cleaned = pattern.sub(" ", name_cleaned)

    name_cleaned = re.sub(r"\s+", " ", name_cleaned).strip()

    return name_cleaned
