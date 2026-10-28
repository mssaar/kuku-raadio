from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from kuku.live import Schedule, should_record_now

tz = ZoneInfo("Europe/Tallinn")
now = datetime(2026, 10, 10, 11, 55, tzinfo=tz)

schedule = Schedule(show_id=175, name="Keskpäevatund", weekday=5, hour=12, duration_minutes=60)
print("Should record:", should_record_now(schedule, now))
