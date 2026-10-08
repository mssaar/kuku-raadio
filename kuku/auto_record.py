"""Automaatne Kuku saadete otse-eetrist salvestaja (käivitatakse cron-ist)."""

import sys
import subprocess
from datetime import datetime, timezone, timedelta
import pytz

from kuku.live import Schedule, should_record_now
from kuku.api import KukuClient

# Saate graafik (Eesti aja järgi)
SCHEDULES = [
    Schedule(show_id=214, name="Buum", weekday=2, hour=13, duration_minutes=60),
    Schedule(show_id=111513, name="Jäljed gloobusel", weekday=3, hour=11, duration_minutes=60)
]

def is_previous_episode_premium(show_id: int) -> bool:
    client = KukuClient()
    since = datetime.now(timezone.utc) - timedelta(days=30)
    try:
        episodes = client.list_episodes(show_id, since)
        if not episodes:
            return True # Vaikimisi salvestame, kui ei leia ajalugu
        episodes.sort(key=lambda e: e.published_at, reverse=True)
        return episodes[0].is_premium
    except Exception as e:
        print(f"Viga API kontrollimisel: {e}")
        return True # Vea korral pigem salvestame otse

def main():
    tz = pytz.timezone("Europe/Tallinn")
    now = datetime.now(tz)
    print(f"Praegune aeg (Tallinn): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    for schedule in SCHEDULES:
        if should_record_now(schedule, now):
            print(f"Kontrollin, kas '{schedule.name}' eelmine osa on tasuline...")
            if is_previous_episode_premium(schedule.show_id):
                print(f"Eelmine osa on tasuline (või info puudub). Käivitan '{schedule.name}' otse-salvestuse!")
                cmd = [
                    sys.executable, "-m", "kuku.record_live",
                    "--show-id", str(schedule.show_id),
                    "--show-name", schedule.name,
                    "--episode-title", f"{schedule.name} ({now.strftime('%d.%m.%Y')})",
                    "--duration", str(schedule.duration_minutes),
                    "--ad-times", "auto"
                ]
                subprocess.run(cmd, check=True)
                return
            else:
                print(f"'{schedule.name}' eelmine osa on tasuta tõmmatav. Jätan otse-salvestuse vahele.")
                return
            
    print("Praegu ei ole ühtegi salvestamist vajavat saadet eetris.")

if __name__ == "__main__":
    main()
