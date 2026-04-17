from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    lib_torrent_port: int = Field(6881)
    port: int = Field(4300)
    relay_auto_start: bool = Field(False)

    base_data_dir: Path = Field(
        default=Path(__file__).resolve().parent.parent.parent / "data"
    )

    @property
    def downloads_dir(self) -> Path:
        return self.base_data_dir / "downloads"

    @property
    def resume_data_dir(self) -> Path:
        return self.base_data_dir / "system" / "resumes"


config = Config()  # type: ignore[call-arg]
