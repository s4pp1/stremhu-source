from pydantic import BaseModel


class Health(BaseModel):
    ok: bool
