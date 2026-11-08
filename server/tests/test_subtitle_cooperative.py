import asyncio

import pytest

from app.modules.stream.utils import subtitles
from app.modules.stream.utils.subtitles import (
    ass_to_vtt,
    ass_to_vtt_cooperative,
    decode_subtitle_text,
    decode_subtitle_text_cooperative,
)

HEADER = "[Script Info]\nTitle: x\n\n[V4+ Styles]\nStyle: Default,Arial\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"


def ass(newline: str) -> str:
    lines = []
    for i in range(300):
        text = f"{{\\i1}}Sor {i}, árvíztűrő\\Nmásodik{{\\i0}}" if i % 3 else f"{{\\p1}}m 0 0 l {i} 0{{\\p0}}"
        lines.append(f"Dialogue: 0,0:00:{i % 60:02d}.{i % 100:02d},0:01:00.00,Default,,0,0,0,,{text}")
        if i == 150:
            lines.append("[Fonts]")
            lines.append("Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,outside events")
            lines.append("[Events]")
    return HEADER.replace("\n", newline) + newline.join(lines) + newline


@pytest.mark.anyio
@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r", " "])
@pytest.mark.parametrize("chars_per_slice", [1, 7, 64, 4096, 32 * 1024])
async def test_cooperative_conversion_is_identical_to_sync(newline, chars_per_slice):
    content = ass(newline)
    assert await ass_to_vtt_cooperative(content, chars_per_slice) == ass_to_vtt(content)


@pytest.mark.anyio
async def test_cooperative_conversion_of_empty_input_matches_sync():
    assert await ass_to_vtt_cooperative("") == ass_to_vtt("") == "WEBVTT\n"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "raw",
    [
        "﻿Árvíztűrő tükörfúrógép\n".encode() * 50,
        "Árvíztűrő tükörfúrógép\n".encode() * 50,
        "Árvíztűrő tükörfúrógép\n".encode("cp1250") * 50,
        "Árvíztűrő\n".encode() * 40 + b"\xff",  # invalid UTF-8 only at the very end
        "Árvíztűrő".encode()[:-1],  # truncated multibyte sequence at the end
    ],
)
async def test_cooperative_decode_matches_sync_rule_across_slice_boundaries(monkeypatch, raw):
    monkeypatch.setattr(subtitles, "_DECODE_BYTES_PER_SLICE", 3)
    assert await decode_subtitle_text_cooperative(raw) == decode_subtitle_text(raw)


@pytest.mark.anyio
async def test_event_loop_runs_between_conversion_slices():
    content = ass("\n")
    beats = 0
    stop = asyncio.Event()

    async def heartbeat():
        nonlocal beats
        while not stop.is_set():
            beats += 1
            await asyncio.sleep(0)

    task = asyncio.create_task(heartbeat())
    await asyncio.sleep(0)
    before = beats
    raw = content.encode()
    slices = len(raw) // 1024
    result = await ass_to_vtt_cooperative(await decode_subtitle_text_cooperative(raw), 1024)
    during = beats - before
    stop.set()
    await task
    assert result == ass_to_vtt(content)
    # One heartbeat per yielded slice: the loop was not blocked for the whole conversion.
    assert during >= slices
