"""SP02 (graded start) and SP01 (byte-based readahead window) behind config switches.

The handle double follows the native semantics measured in G0 (libtorrent 2.1.1):
a deadline raises the piece to priority 7, and reset_piece_deadline leaves an
unfinished piece at priority 1. The legacy policy must produce today's deadlines.
"""

from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.common.constants import PRIO_0
from app.config import config
from app.modules.relay.entities import File, Stream, Torrent

MIB = 1024 * 1024


class FakeHandle:
    def __init__(self, pieces: int, have: set[int] | None = None):
        self.pieces = pieces
        self.have = set(have or ())
        self.deadlines: dict[int, int] = {}
        self.priority = [PRIO_0] * pieces
        self.have_piece_calls = 0
        self.status_calls = 0
        self.fail_status = False

    def have_piece(self, index: int) -> bool:
        self.have_piece_calls += 1
        return index in self.have

    def status(self, flags=None):
        self.status_calls += 1
        if self.fail_status:
            raise RuntimeError("synthetic native failure")
        return SimpleNamespace(pieces=[i in self.have for i in range(self.pieces)])

    def set_piece_deadline(self, index: int, deadline: int) -> None:
        self.deadlines[index] = deadline
        self.priority[index] = 7

    def reset_piece_deadline(self, index: int) -> None:
        self.deadlines.pop(index, None)
        if index not in self.have:
            self.priority[index] = 1  # G0: not back to 0

    def piece_priority(self, index: int, priority: int) -> None:
        self.priority[index] = priority

    def piece_priorities(self) -> list[int]:
        return list(self.priority)

    def prioritize_pieces(self, priorities: list[int]) -> None:
        self.priority = list(priorities)


def make_torrent(piece_size: int, pieces: int, have: set[int] | None = None) -> tuple[Torrent, File, FakeHandle]:
    handle = FakeHandle(pieces, have)
    torrent = object.__new__(Torrent)
    torrent.torrent_handle = cast(Any, handle)
    torrent.service = cast(Any, SimpleNamespace(apply_torrent_connection_policy=lambda _: None))
    torrent.info_hash = "0" * 40
    torrent.piece_size = piece_size
    torrent.total_size = piece_size * pieces
    torrent.piece_count = pieces
    torrent.critical_piece_count = max(1, min(-(-MIB // piece_size), 2))
    torrent.prefetch_piece_count = torrent.critical_piece_count * 4
    torrent._default_piece_priority = PRIO_0
    torrent._current_piece_priority = PRIO_0
    torrent._active_deadlines = {}
    file = File(cast(Any, SimpleNamespace(name="movie.mkv", size=piece_size * pieces, offset=0, index=0)), torrent)
    torrent.files = {0: file}
    return torrent, file, handle


def stream_at(torrent: Torrent, file: File, piece: int) -> Stream:
    stream = Stream("s", "p", "u", torrent, file, 0, file.size - 1)
    stream.current_stream_piece = piece
    return stream


@pytest.fixture
def policy(monkeypatch):
    def set_policy(start: str = "legacy", readahead: str = "legacy", **values: int) -> None:
        monkeypatch.setattr(config, "relay_start_policy", start)
        monkeypatch.setattr(config, "relay_readahead_policy", readahead)
        for key, value in values.items():
            monkeypatch.setattr(config, key, value)

    set_policy()
    return set_policy


def test_legacy_policy_keeps_todays_deadlines(policy):
    torrent, file, handle = make_torrent(MIB, 20)
    stream_at(torrent, file, 5)
    assert torrent.get_deadlines() == {0: 0, 1: 0, 2: 0, 17: 0, 18: 0, 19: 0, 5: 0, 6: 300, 7: 2000, 8: 2500}
    assert handle.status_calls == 0  # the legacy path is unchanged


def test_window_is_byte_based_monotonic_and_reads_one_bitfield(policy):
    policy(start="graded", readahead="window", relay_readahead_bytes=16 * MIB,
           relay_readahead_assumed_rate_bytes=8_000_000, relay_tail_bytes=MIB)
    torrent, file, handle = make_torrent(MIB, 40)
    stream_at(torrent, file, 0)
    deadlines = torrent.get_deadlines()
    window = {k: v for k, v in deadlines.items() if k < 39}
    assert sorted(window) == list(range(16))
    assert window[0] == 0 and window[1] == 300 and window[2] == 1000 + int(2 * MIB * 1000 / 8_000_000)
    assert [window[i] for i in range(16)] == sorted(window[i] for i in range(16))
    assert deadlines[39] == 200  # graded tail
    assert handle.status_calls == 1 and handle.have_piece_calls == 0


@pytest.mark.parametrize(("piece_size", "expected"), [(4 * MIB, 4), (16 * MIB, 4), (512 * 1024, 32)])
def test_window_size_follows_bytes_with_a_four_piece_minimum(policy, piece_size, expected):
    policy(readahead="window", relay_readahead_bytes=16 * MIB)
    torrent, file, _ = make_torrent(piece_size, 200)
    stream_at(torrent, file, 100)
    deadlines = torrent.get_deadlines()
    assert sorted(k for k in deadlines if 100 <= k < 197) == list(range(100, 100 + expected))


def test_window_is_capped_by_max_pieces(policy):
    policy(readahead="window", relay_readahead_bytes=1024 * MIB, relay_readahead_max_pieces=128)
    torrent, file, _ = make_torrent(MIB, 400)
    stream_at(torrent, file, 10)
    assert len([k for k in torrent.get_deadlines() if 10 <= k < 397]) == 128


def test_window_skips_downloaded_pieces_and_wraps_like_legacy(policy):
    policy(readahead="window", relay_readahead_bytes=4 * MIB)
    torrent, file, _ = make_torrent(MIB, 10, have={9, 0, 1, 2, 7})
    stream_at(torrent, file, 8)
    deadlines = torrent.get_deadlines()
    # forward: 8 (have 9); then wrap from the file start, skipping downloaded pieces
    assert {k for k, v in deadlines.items() if k in (8, 3, 4, 5)} == {8, 3, 4, 5}
    assert deadlines[8] == 0


def test_two_streams_take_the_earliest_deadline(policy):
    policy(readahead="window", relay_readahead_bytes=8 * MIB)
    torrent, file, _ = make_torrent(MIB, 100)
    first = stream_at(torrent, file, 10)
    second = Stream("s2", "p2", "u", torrent, file, 0, file.size - 1)
    second.current_stream_piece = 12
    deadlines = torrent.get_deadlines()
    assert deadlines[12] == 0 and deadlines[10] == 0
    assert first.current_stream_piece == 10


def test_destroying_stream_is_ignored(policy):
    policy(readahead="window")
    torrent, file, _ = make_torrent(MIB, 100)
    stream_at(torrent, file, 50).is_destroying = True
    assert not any(40 <= k < 97 for k in torrent.get_deadlines())


def test_graded_start_keeps_only_the_stream_piece_urgent(policy):
    policy(start="graded", relay_head_bytes=2 * MIB, relay_tail_bytes=4 * MIB)
    torrent, file, _ = make_torrent(4 * MIB, 50)
    stream_at(torrent, file, 0)
    deadlines = torrent.get_deadlines()
    assert [k for k, v in deadlines.items() if v == 0] == [0]
    assert deadlines[49] == 200 and 47 not in deadlines and 48 not in deadlines


def test_graded_start_after_a_seek_and_byte_bounded_tail(policy):
    policy(start="graded", relay_head_bytes=2 * MIB, relay_tail_bytes=4 * MIB)
    torrent, file, _ = make_torrent(MIB, 50)
    stream_at(torrent, file, 25)
    deadlines = torrent.get_deadlines()
    assert deadlines[0] == 1000 and deadlines[1] == 1200  # head no longer urgent mid-file
    assert [deadlines[i] for i in (49, 48, 47, 46)] == [200, 1200, 1400, 1600]
    assert 45 not in deadlines


def test_bitfield_failure_falls_back_to_the_legacy_path(policy):
    policy(start="graded", readahead="window")
    torrent, file, handle = make_torrent(MIB, 20)
    handle.fail_status = True
    stream_at(torrent, file, 5)
    assert torrent.get_deadlines() == {0: 0, 1: 0, 2: 0, 17: 0, 18: 0, 19: 0, 5: 0, 6: 300, 7: 2000, 8: 2500}


@pytest.mark.parametrize(("readahead", "dropped_priority"), [("window", PRIO_0), ("legacy", 1)])
def test_dropped_window_pieces_return_to_the_background_priority(policy, readahead, dropped_priority):
    policy(readahead=readahead, relay_readahead_bytes=4 * MIB)
    torrent, file, handle = make_torrent(MIB, 100)
    stream = stream_at(torrent, file, 10)
    torrent.priority_manager()
    assert handle.deadlines.get(11) == 300
    stream.current_stream_piece = 60  # seek
    torrent.priority_manager()
    assert 11 not in handle.deadlines
    # window: back to the streaming background (0); legacy keeps today's leak (1).
    assert handle.priority[11] == dropped_priority


def test_upstream_like_candidate_matches_the_upstream_deadlines(policy):
    # s4pp1/stremhu-source@8c99c7d: first and last piece urgent; window 0 / 2000 + 1000*d ms.
    policy(start="edges", readahead="upstream")
    torrent, file, handle = make_torrent(MIB, 20)
    stream_at(torrent, file, 5)
    assert torrent.get_deadlines() == {0: 0, 19: 0, 5: 0, 6: 3000, 7: 4000, 8: 5000}
    assert handle.status_calls == 1 and handle.have_piece_calls == 0


def test_upstream_like_window_skips_downloaded_pieces_and_wraps(policy):
    policy(start="edges", readahead="upstream")
    torrent, file, _ = make_torrent(4 * MIB, 10, have={0, 9, 8})
    stream_at(torrent, file, 7)
    # 4 MiB pieces -> 4-piece window: 7, then wrap to 1, 2, 3 (0, 8, 9 downloaded); edges already present.
    deadlines = torrent.get_deadlines()
    assert deadlines == {7: 0, 1: 2000 + 4000, 2: 2000 + 5000, 3: 2000 + 6000}


def test_focus_gives_the_awaited_piece_exclusive_priority(policy):
    policy(start="edges", readahead="focus")
    torrent, file, handle = make_torrent(16 * MIB, 64, have={0, 63})
    stream_at(torrent, file, 32)  # e.g. right after a seek: piece 32 is missing
    assert torrent.get_deadlines() == {32: 0}
    assert handle.status_calls == 1


def test_focus_runs_the_tight_window_once_the_awaited_piece_is_present(policy):
    policy(start="edges", readahead="focus")
    torrent, file, _ = make_torrent(MIB, 20, have={0, 19, 5})
    stream_at(torrent, file, 5)
    # piece 5 present -> legacy window from 6: 300 ms, then 1000 + 500*d
    assert torrent.get_deadlines() == {6: 300, 7: 2000, 8: 2500, 9: 3000}


def test_focus_returns_dropped_window_pieces_to_the_background(policy):
    policy(start="edges", readahead="focus")
    torrent, file, handle = make_torrent(MIB, 100, have={0, 99, 10})
    stream = stream_at(torrent, file, 10)
    torrent.priority_manager()
    assert handle.deadlines.get(12) == 2000
    stream.current_stream_piece = 60  # seek to a missing piece -> focus on it alone
    torrent.priority_manager()
    assert handle.deadlines == {60: 0}
    assert handle.priority[12] == PRIO_0


def test_focus_with_a_parallel_tail_probe_keeps_both_awaited_pieces(policy):
    policy(start="edges", readahead="focus")
    torrent, file, _ = make_torrent(16 * MIB, 64)
    stream_at(torrent, file, 0)
    tail = Stream("tail", "p", "u", torrent, file, file.size - 1024, file.size - 1)
    tail.current_stream_piece = 63
    assert torrent.get_deadlines() == {0: 0, 63: 0}


def test_startfocus_is_exclusive_only_for_the_first_piece_of_a_stream(policy):
    policy(start="edges", readahead="startfocus")
    torrent, file, _ = make_torrent(16 * MIB, 64, have={0, 63})
    seek = Stream("seek", "p", "u", torrent, file, 32 * 16 * MIB, file.size - 1)
    assert seek.current_stream_piece == 32
    assert torrent.get_deadlines() == {32: 0}  # right after a seek: all peers on the awaited piece


def test_startfocus_runs_the_window_after_the_first_piece(policy):
    policy(start="edges", readahead="startfocus")
    torrent, file, _ = make_torrent(MIB, 20, have={0, 19, 5})
    stream = Stream("s", "p", "u", torrent, file, 5 * MIB, file.size - 1)
    stream.current_stream_piece = 6  # the first piece (5) was delivered; piece 6 is missing
    # no exclusivity any more: the legacy window from 6 (0, 300, 1000 + 500*d)
    assert torrent.get_deadlines() == {6: 0, 7: 300, 8: 2000, 9: 2500}


def test_defaults_are_the_gate_passed_upstream_like_start_and_legacy_stays_selectable():
    # gsp02-v4 PASS:C2 (2026-11-10): edges start + upstream deadlines by default; legacy for rollback.
    from typing import get_args

    from app.config import Config

    fields = Config.model_fields
    assert fields["relay_start_policy"].default == "edges"
    assert fields["relay_readahead_policy"].default == "upstream"
    assert "legacy" in get_args(fields["relay_start_policy"].annotation)
    assert "legacy" in get_args(fields["relay_readahead_policy"].annotation)


def test_upstream_like_path_falls_back_when_the_torrent_has_no_piece_count(policy):
    policy(start="edges", readahead="upstream")
    torrent, file, handle = make_torrent(MIB, 20)
    del torrent.piece_count  # e.g. an object built without __init__
    stream_at(torrent, file, 5)
    # falls back to the legacy path instead of raising
    assert torrent.get_deadlines() == {0: 0, 1: 0, 2: 0, 17: 0, 18: 0, 19: 0, 5: 0, 6: 300, 7: 2000, 8: 2500}
