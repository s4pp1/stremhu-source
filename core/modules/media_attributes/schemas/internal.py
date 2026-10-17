from pydantic import BaseModel


class MediaAttributeFilter(BaseModel):
    user_id: str | None = None
    not_added_to_preference: bool = False
