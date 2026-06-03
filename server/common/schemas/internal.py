from pydantic import BaseModel


class Success(BaseModel):
    success: bool
    message: str | None = None
