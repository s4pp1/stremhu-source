import time
from typing import Any

from app.config import config
from app.modules.hls_stream.metadata_probe import MediaMetadata, MetadataProbe
from app.modules.relay.entities import File


class HlsStreamService:
    def __init__(self):
        # Cache memory structure:
        # { "stream_token": { "metadata": MediaMetadata, "keyframes": list[float], "expires": timestamp } }
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl = 3600  # 1 hour

    def _cleanup_cache(self):
        now = time.time()
        to_delete = [k for k, v in self._cache.items() if v["expires"] < now]
        for k in to_delete:
            del self._cache[k]

    async def get_or_probe_stream(
        self,
        stream_token_str: str,
        stream_token: Any,
        user: Any,
        api_key: str,
        relay_file: File,
    ) -> tuple[MediaMetadata, list[float]]:
        self._cleanup_cache()

        cached = self._cache.get(stream_token_str)
        if cached:
            cached["expires"] = time.time() + self._cache_ttl
            return cached["metadata"], cached["keyframes"]

        # Local internal URL to feed to ffprobe
        local_stream_url = (
            f"https://127.0.0.1:{config.port}/api/{api_key}/stream/{stream_token_str}"
        )

        probe = MetadataProbe(local_stream_url)
        metadata = await probe.probe()

        if not metadata:
            metadata = MediaMetadata(duration=0, video_stream=None, audio_streams=[])

        # Állandó 6 másodperces chunkok generálása a videó hossza alapján
        keyframes = []
        if metadata.duration > 0:
            current_time = 0.0
            while current_time < metadata.duration:
                keyframes.append(current_time)
                current_time += 6.0
        else:
            keyframes = [0.0]

        self._cache[stream_token_str] = {
            "metadata": metadata,
            "keyframes": keyframes,
            "expires": time.time() + self._cache_ttl,
        }

        return metadata, keyframes

    def get_chunk_info(
        self, stream_token_str: str, chunk_id: int
    ) -> tuple[float, float] | None:
        """
        Returns (start_time, duration) for a given chunk index.
        """
        cached = self._cache.get(stream_token_str)
        if not cached:
            return None

        keyframes: list[float] = cached["keyframes"]
        metadata: MediaMetadata = cached["metadata"]

        if not keyframes:
            # Fallback
            start_time = float(chunk_id) * 6.0
            duration = 6.0
            if start_time > metadata.duration:
                return None
            return (start_time, duration)

        if chunk_id >= len(keyframes):
            return None

        start_time = keyframes[chunk_id]

        if chunk_id < len(keyframes) - 1:
            end_time = keyframes[chunk_id + 1]
        else:
            end_time = metadata.duration

        duration = end_time - start_time
        return (start_time, duration)


# Global service instance
hls_stream_service = HlsStreamService()


def get_hls_stream_service() -> HlsStreamService:
    return hls_stream_service
