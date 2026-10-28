from datetime import datetime, timezone, timedelta
from kuku.api import KukuClient
import sys

client = KukuClient()
since = datetime.now(timezone.utc) - timedelta(days=60)
try:
    episodes = client.list_episodes(175, since)
    if not episodes:
        print("No recent episodes found in 60 days.")
        sys.exit(0)
    episodes.sort(key=lambda e: e.published_at, reverse=True)
    
    print(f"Latest episode of Keskpäevatund:")
    for i, e in enumerate(episodes[:3]):
        print(f"{i+1}. ID: {e.id}, Title: {e.title}, Published: {e.published_at.astimezone().isoformat()}, Premium: {e.is_premium}")
except Exception as e:
    print(f"Error checking API: {e}")
