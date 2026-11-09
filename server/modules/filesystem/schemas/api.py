from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class DirectoryEntry(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )
    name: str
    path: str


class BrowseDirectoriesResponse(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )
    current_path: str
    parent_path: str | None
    directories: list[DirectoryEntry]


class CreateDirectoryRequest(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )
    parent_path: str
    name: str


class CreateDirectoryResponse(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )
    path: str
