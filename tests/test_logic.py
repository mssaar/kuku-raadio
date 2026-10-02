from datetime import datetime, timedelta, timezone

from kuku.api import Episode
from kuku.logic import cutoff, expires_at, is_expired, looks_like_full_mp3, select_new

NOW = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)


def ep(id, days_ago, premium=False, playable=True):
    return Episode(id, f"Osa {id}", NOW - timedelta(days=days_ago), premium, playable, 2800.0)


def test_select_new_keeps_free_unstored_recent():
    eps = [ep(5, 1), ep(4, 8), ep(3, 15, premium=True), ep(2, 22, playable=False), ep(1, 200)]
    assert [e.id for e in select_new(eps, stored_ids={5}, now=NOW)] == [4]


def test_select_new_orders_oldest_first():
    assert [e.id for e in select_new([ep(2, 1), ep(1, 8)], set(), NOW)] == [1, 2]


def test_expiry_is_182_days():
    published = NOW - timedelta(days=10)
    assert expires_at(published) == published + timedelta(days=182)
    assert cutoff(NOW) == NOW - timedelta(days=182)
    assert not is_expired(NOW - timedelta(days=181), NOW)
    assert is_expired(NOW - timedelta(days=183), NOW)


def test_looks_like_full_mp3():
    big = 2800 * 8000
    assert looks_like_full_mp3(b"ID3\x04", big, 2800)
    assert looks_like_full_mp3(b"\xff\xfb\x90\x00", big, 2800)
    assert not looks_like_full_mp3(b"<htm", big, 2800)
    assert not looks_like_full_mp3(b"ID3\x04", 70 * 40000, 2800)  # ~1 min teaser
