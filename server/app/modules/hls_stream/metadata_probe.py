import json
from dataclasses import dataclass
from typing import Any

import pydash

from app.common.logger import logger


@dataclass
class VideoStreamInfo:
    codec: str
    width: int
    height: int
    profile: str
    is_hdr: bool
    is_dv: bool


@dataclass
class AudioStreamInfo:
    index: int
    codec: str
    channels: int
    language: str


@dataclass
class MediaMetadata:
    duration: float
    video_stream: VideoStreamInfo | None
    audio_streams: list[AudioStreamInfo]


class MetadataProbe:
    def __init__(self, stream_url: str):
        self.stream_url = stream_url

    async def probe(self) -> MediaMetadata | None:
        """
        Runs ffprobe on the stream URL to extract metadata.
        """
        command = [
            "ffprobe",
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            "-analyzeduration", "10000000",
            "-probesize", "5000000",
            self.stream_url
        ]

        try:
            logger.info(f"Running ffprobe on {self.stream_url}")
            # Run ffprobe using subprocess. It is IO-bound, we can use asyncio.to_thread or run synchronously.
            # It's better to use asyncio.create_subprocess_exec for non-blocking.
            import asyncio
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"ffprobe failed: {stderr.decode()}")
                return None

            data = json.loads(stdout.decode())
            return self._parse_ffprobe_data(data)

        except Exception:
            logger.exception("Error probing metadata")
            return None

    def _parse_ffprobe_data(self, data: dict[str, Any]) -> MediaMetadata:
        duration = float(pydash.get(data, "format.duration", 0.0))

        video_stream_info = None
        audio_streams = []

        for stream in pydash.get(data, "streams", []):
            if pydash.get(stream, "codec_type") == "video" and not video_stream_info:
                # Basic HDR/DV check based on color space or profile
                color_transfer = pydash.get(stream, "color_transfer", "")
                profile = pydash.get(stream, "profile", "")

                is_hdr = "smpte2084" in color_transfer or "arib-std-b67" in color_transfer
                is_dv = "dovi" in pydash.get(stream, "codec_name", "").lower() or "dovi" in profile.lower()

                video_stream_info = VideoStreamInfo(
                    codec=pydash.get(stream, "codec_name", ""),
                    width=int(pydash.get(stream, "width", 0)),
                    height=int(pydash.get(stream, "height", 0)),
                    profile=profile,
                    is_hdr=is_hdr,
                    is_dv=is_dv
                )
            elif pydash.get(stream, "codec_type") == "audio":
                tags = pydash.get(stream, "tags", {})
                language = pydash.get(tags, "language", "und")
                audio_streams.append(
                    AudioStreamInfo(
                        index=pydash.get(stream, "index"),
                        codec=pydash.get(stream, "codec_name", ""),
                        channels=pydash.get(stream, "channels", 2),
                        language=language
                    )
                )

        return MediaMetadata(
            duration=duration,
            video_stream=video_stream_info,
            audio_streams=audio_streams
        )
