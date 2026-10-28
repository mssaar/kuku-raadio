from datetime import datetime, timezone, timedelta
from kuku.api import KukuClient

def is_previous_episode_premium(show_id: int) -> bool:
    client = KukuClient()
    since = datetime.now(timezone.utc) - timedelta(days=30)
    try:
        episodes = client.list_episodes(show_id, since)
        if not episodes:
            return False
        episodes.sort(key=lambda e: e.published_at, reverse=True)
        # return the premium status of the latest one
        return episodes[0].is_premium
    except Exception as e:
        print(f"Error checking API: {e}")
        return False

print("Buum (214):", is_previous_episode_premium(214))
print("Digitund (209):", is_previous_episode_premium(209))
