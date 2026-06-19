from app.modules.hls_stream.metadata_probe import MediaMetadata


class HlsManifestGenerator:
    @staticmethod
    def generate_master_playlist(stream_token: str, metadata: MediaMetadata) -> str:
        """
        Generál egy Master M3U8 fájlt a felderített adatok alapján.
        """
        lines = [
            "#EXTM3U",
            "#EXT-X-VERSION:3",
        ]

        # Eredeti minőség (Remux)
        if metadata.video_stream:
            width = metadata.video_stream.width
            height = metadata.video_stream.height
            resolution_str = f"{width}x{height}" if width and height else "1920x1080"

            lines.append(
                f'#EXT-X-STREAM-INF:BANDWIDTH=15000000,RESOLUTION={resolution_str},NAME="Original"'
            )
            lines.append("variant/original/index.m3u8")

            # Ha HDR/DV vagy 4K, felajánlunk egy SDR transzkódolt verziót is
            if (
                metadata.video_stream.is_hdr
                or metadata.video_stream.is_dv
                or width >= 3840
            ):
                lines.append(
                    '#EXT-X-STREAM-INF:BANDWIDTH=8000000,RESOLUTION=1920x1080,NAME="SDR 1080p"'
                )
                lines.append("variant/sdr_1080p/index.m3u8")
        else:
            # Csak hang vagy ismeretlen, legyen egy default
            lines.append('#EXT-X-STREAM-INF:BANDWIDTH=15000000,NAME="Original"')
            lines.append("variant/original/index.m3u8")

        return "\n".join(lines) + "\n"

    @staticmethod
    def generate_media_playlist(keyframes: list[float], duration: float) -> str:
        """
        Generál egy változó szegmenshosszúságú (VOD) Media Playlistet (index.m3u8).
        """
        if not keyframes:
            # Ha nincsenek kulcskockák, fallback egy fix hosszakra (pl 6s)
            keyframes = [i * 6.0 for i in range(int(duration / 6.0) + 1)]

        # Ensure 0.0 is the first keyframe
        if not keyframes or keyframes[0] > 0.1:
            keyframes.insert(0, 0.0)

        lines = [
            "#EXTM3U",
            "#EXT-X-VERSION:3",
            "#EXT-X-TARGETDURATION:15",  # Maximum segment length approx
            "#EXT-X-MEDIA-SEQUENCE:0",
            "#EXT-X-PLAYLIST-TYPE:VOD",
        ]

        # Calculate max duration
        max_duration = 0.0
        segments = []
        for i in range(len(keyframes) - 1):
            length = keyframes[i + 1] - keyframes[i]
            if length > 0:
                segments.append((length, keyframes[i], i))
                max_duration = max(max_duration, length)

        # Add the final segment
        if keyframes and duration > keyframes[-1]:
            length = duration - keyframes[-1]
            segments.append((length, keyframes[-1], len(keyframes) - 1))
            max_duration = max(max_duration, length)

        lines[2] = f"#EXT-X-TARGETDURATION:{int(max_duration) + 1}"

        for length, _start_time, index in segments:
            lines.append(f"#EXTINF:{length:.6f},")
            lines.append(f"chunk_{index}.ts")

        lines.append("#EXT-X-ENDLIST")

        return "\n".join(lines) + "\n"
