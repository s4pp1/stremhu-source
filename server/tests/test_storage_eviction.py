from app.modules.storage.utils import (
    GIB,
    MAX_RESERVE_BYTES,
    plan_eviction,
    reserve_bytes,
)


def test_no_eviction_when_enough_space():
    assert plan_eviction(10 * GIB, 5 * GIB, [("a", 3 * GIB)]) == []


def test_evicts_oldest_first_only_as_much_as_needed():
    candidates = [("old", 2 * GIB), ("mid", 3 * GIB), ("new", 4 * GIB)]
    assert plan_eviction(1 * GIB, 5 * GIB, candidates) == ["old", "mid"]


def test_evicts_all_candidates_when_still_not_enough():
    candidates = [("a", 1 * GIB), ("b", 1 * GIB)]
    assert plan_eviction(0, 10 * GIB, candidates) == ["a", "b"]


def test_zero_sized_candidate_is_skipped_over_but_still_selected():
    candidates = [("empty", 0), ("big", 5 * GIB)]
    assert plan_eviction(0, 4 * GIB, candidates) == ["empty", "big"]


def test_reserve_is_five_percent_capped():
    assert reserve_bytes(20 * GIB) == GIB
    assert reserve_bytes(1024 * GIB) == MAX_RESERVE_BYTES
    assert reserve_bytes(0) == 0
