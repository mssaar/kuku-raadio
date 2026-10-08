
import pytest
from datetime import datetime, timezone, timedelta
import pytz
from kuku.live import Schedule
from kuku.api import Episode

def get_premiere_schedules(episodes: list[Episode], show_id: int, show_name: str) -> list[Schedule]:
    tz = pytz.timezone('Europe/Tallinn')
    schedules = set()
    for ep in episodes[:5]:
        dt = ep.published_at.astimezone(tz)
        schedules.add((dt.weekday(), dt.hour))
    return [Schedule(show_id=show_id, name=show_name, weekday=w, hour=h, duration_minutes=60) for w, h in schedules]

def test_get_premiere_schedules():
    tz = pytz.timezone('Europe/Tallinn')
    # 2 episoodi kolmapäeval kell 13:00
    ep1 = Episode(id=1, title='Esimene', published_at=tz.localize(datetime(2026, 10, 7, 13, 0)).astimezone(timezone.utc), is_premium=False, is_playable=True, duration_seconds=3600)
    ep2 = Episode(id=2, title='Teine', published_at=tz.localize(datetime(2026, 9, 30, 13, 0)).astimezone(timezone.utc), is_premium=False, is_playable=True, duration_seconds=3600)
    schedules = get_premiere_schedules([ep1, ep2], 214, 'Buum')
    assert len(schedules) == 1
    assert schedules[0].weekday == 2
    assert schedules[0].hour == 13

