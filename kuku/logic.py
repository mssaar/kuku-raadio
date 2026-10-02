"""Puhtad reeglid: milliseid osi laadida ja millal neid kustutada."""

from datetime import timedelta

RETENTION = timedelta(days=182)
MIN_BYTES_PER_SECOND = 8000  # 64 kbit/s; tasuliste osade teaser on ~1 min


def cutoff(now):
    return now - RETENTION


def expires_at(published_at):
    return published_at + RETENTION


def is_expired(published_at, now):
    return published_at < cutoff(now)


def select_new(episodes, stored_ids, now):
    fresh = [e for e in episodes
             if not e.is_premium and e.is_playable
             and e.id not in stored_ids and not is_expired(e.published_at, now)]
    return sorted(fresh, key=lambda e: e.published_at)


def looks_like_full_mp3(head, size, duration_seconds):
    is_mp3 = head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0)
    return is_mp3 and size >= duration_seconds * MIN_BYTES_PER_SECOND
