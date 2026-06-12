from pydantic import BaseModel


class AttributeExclusionCreate(BaseModel):
    attribute_id: str
    user_id: str | None


class AttributeExclusionUpdate(BaseModel):
    attribute_id: str | None = None
    user_id: str | None = None


class AttributeExclusionFilter(BaseModel):
    attribute_id: str | None = None
    user_id: str | None = None
