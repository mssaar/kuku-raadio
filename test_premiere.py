from datetime import datetime, timezone, timedelta
from kuku.api import KukuClient
from zoneinfo import ZoneInfo

client = KukuClient()
since = datetime.now(timezone.utc) - timedelta(days=60)
episodes = client.list_episodes(175, since)
episodes.sort(key=lambda e: e.published_at, reverse=True)

tz = ZoneInfo('Europe/Tallinn')
schedules = set()
for ep in episodes[:5]:
    dt = ep.published_at.astimezone(tz)
    schedules.add((dt.weekday(), dt.hour))
    
for w, h in schedules:
    print(f"Schedule: weekday {w}, hour {h}")
