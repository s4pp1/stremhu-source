import asyncio
import logging
import shutil
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class TranscodeSession:
    def __init__(self, stream_token: str, profile_id: str, stream_url: str):
        self.stream_token = stream_token
        self.profile_id = profile_id
        self.stream_url = stream_url

        # Ideiglenes mappa a darabkáknak
        self.temp_dir = (
            Path(tempfile.gettempdir()) / f"stremhu_hls_{stream_token}_{profile_id}"
        )
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.process: asyncio.subprocess.Process | None = None
        self.current_start_chunk: int = -1
        self.last_accessed: float = time.time()

        self.lock = asyncio.Lock()

    async def start(self, start_chunk: int, chunk_duration: float = 6.0):
        async with self.lock:
            if self.process:
                try:
                    self.process.terminate()
                    await asyncio.wait_for(self.process.wait(), timeout=2.0)
                except Exception:
                    self.process.kill()
                    await self.process.wait()
                self.process = None

            self.current_start_chunk = start_chunk
            start_time = start_chunk * chunk_duration

            # Az FFmpeg a .conda környezetben van
            command = [
                "/Users/benedekbalint/Development/stremhu-source/server/.conda/bin/ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                str(start_time),
                "-i",
                self.stream_url,
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-sn",
                "-copyts",
                "-muxdelay",
                "0",
            ]

            if self.profile_id == "original":
                command.extend(
                    [
                        "-c:v",
                        "libx264",
                        "-preset",
                        "ultrafast",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        "-ac",
                        "2",
                    ]
                )
            elif self.profile_id == "sdr_1080p":
                command.extend(
                    [
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "23",
                        "-vf",
                        "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,scale=-2:1080",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        "-ac",
                        "2",
                    ]
                )
            else:
                # Fallback
                command.extend(
                    [
                        "-c:v",
                        "libx264",
                        "-preset",
                        "ultrafast",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        "-ac",
                        "2",
                    ]
                )

            playlist_path = self.temp_dir / "index.m3u8"
            segment_path = self.temp_dir / "chunk_%d.ts"

            command.extend(
                [
                    "-f",
                    "hls",
                    "-hls_time",
                    str(chunk_duration),
                    "-hls_list_size",
                    "0",
                    "-hls_flags",
                    "temp_file",
                    "-start_number",
                    str(start_chunk),
                    "-hls_segment_filename",
                    str(segment_path),
                    str(playlist_path),
                ]
            )

            logger.info(
                f"Starting continuous FFmpeg for chunk {start_chunk}: {' '.join(command)}"
            )
            self.process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

    async def get_chunk_file(
        self, chunk_id: int, chunk_duration: float = 6.0
    ) -> Path | None:
        self.last_accessed = time.time()
        chunk_path = self.temp_dir / f"chunk_{chunk_id}.ts"

        # Ha nagyon ugrál a felhasználó (seeking), vagy az FFmpeg leállt
        if (
            not self.process
            or self.process.returncode is not None
            or chunk_id < self.current_start_chunk
            or chunk_id > self.current_start_chunk + 10
        ):
            if not chunk_path.exists():
                logger.info(
                    f"Seek detected: requested chunk {chunk_id}, current start is {self.current_start_chunk}. Restarting transcoder."
                )
                await self.start(chunk_id, chunk_duration)

        # Várunk maximum 30 másodpercet, amíg a chunk meg nem jelenik
        max_wait = 30.0
        waited = 0.0
        while waited < max_wait:
            if chunk_path.exists():
                return chunk_path

            if self.process and self.process.returncode is not None:
                # Folyamat kilépett, de lehet pont a legutolsó fájlt írta ki
                if chunk_path.exists():
                    return chunk_path
                logger.error(
                    f"FFmpeg process exited unexpectedly with code {self.process.returncode}"
                )
                return None

            await asyncio.sleep(0.5)
            waited += 0.5

        logger.error(f"Timeout waiting for chunk {chunk_id}")
        return None

    def cleanup(self):
        if self.process:
            try:
                self.process.kill()
            except Exception:
                pass
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass


class TranscodeManager:
    def __init__(self):
        self.sessions: dict[str, TranscodeSession] = {}
        # Background task for cleanup
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def get_chunk(
        self,
        stream_token: str,
        profile_id: str,
        stream_url: str,
        chunk_id: int,
        chunk_duration: float = 6.0,
    ) -> Path | None:
        session_id = f"{stream_token}_{profile_id}"
        if session_id not in self.sessions:
            self.sessions[session_id] = TranscodeSession(
                stream_token, profile_id, stream_url
            )

        session = self.sessions[session_id]
        return await session.get_chunk_file(chunk_id, chunk_duration)

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(15)
            now = time.time()
            to_delete = []
            for sid, session in self.sessions.items():
                # Törlés ha 45 másodpercig nem kértek chunkot (a kliens lecsatlakozott vagy megállította)
                if now - session.last_accessed > 45:
                    logger.info(f"Cleaning up inactive transcode session {sid}")
                    session.cleanup()
                    to_delete.append(sid)
            for sid in to_delete:
                del self.sessions[sid]


transcode_manager = TranscodeManager()
