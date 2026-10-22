from pydantic import BaseModel


class PreferenceCreate(BaseModel):
    preference_id: str
    attribute_ids: list[str]


class PreferenceUpdate(BaseModel):
    attribute_ids: list[str]


class PreferencesReorder(BaseModel):
    preference_ids: list[str]
