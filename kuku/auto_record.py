"""Automaatne Kuku saadete otse-eetrist salvestaja (käivitatakse cron-ist)."""

import sys
import sys
import subprocess
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytz

from kuku.live import Schedule, should_record_now, get_premiere_schedules
from kuku.api import KukuClient
from kuku.sync import DATA_DIR

def main():
    tz = pytz.timezone("Europe/Tallinn")
    now = datetime.now(tz)
    print(f"Praegune aeg (Tallinn): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    shows_file = DATA_DIR / "shows.json"
    if not shows_file.exists():
        print("shows.json puudub!")
        return
        
    with open(shows_file, "r", encoding="utf-8") as f:
        my_shows = json.load(f)
        
    client = KukuClient()
    since = datetime.now(timezone.utc) - timedelta(days=60)
    
    for show in my_shows:
        show_id = show["id"]
        show_name = show["name"]
        try:
            episodes = client.list_episodes(show_id, since)
            if not episodes:
                continue
            
            # Tuvastame kõik esmaesituste ajad
            schedules = get_premiere_schedules(episodes, show_id, show_name)
            
            for schedule in schedules:
                if should_record_now(schedule, now):
                    print(f"Esmaesituse aeg sobib! Käivitan '{schedule.name}' otse-salvestuse!")
                    cmd = [
                        sys.executable, "-m", "kuku.record_live",
                        "--show-id", str(schedule.show_id),
                        "--show-name", schedule.name,
                        "--episode-title", f"{schedule.name} ({now.strftime('%d.%m.%Y')})",
                        "--duration", str(schedule.duration_minutes),
                        "--ad-times", "auto"
                    ]
                    subprocess.run(cmd, check=True)
                    return # Salvestame korraga ühe (esimese mis klapib)
        except Exception as e:
            print(f"Viga saate '{show_name}' laadimisel: {e}")
            
    print("Praegu ei ole ühtegi salvestamist vajavat saadet eetris.")

if __name__ == "__main__":
    main()
