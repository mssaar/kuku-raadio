"""Automaatne Kuku saadete otse-eetrist salvestaja (käivitatakse cron-ist)."""

import sys
import subprocess
from datetime import datetime
import pytz

from kuku.live import Schedule, should_record_now

# Saate graafik (Eesti aja järgi)
SCHEDULES = [
    Schedule(show_id=204, name="Buum", weekday=2, hour=13, duration_minutes=60)
]

def main():
    tz = pytz.timezone("Europe/Tallinn")
    now = datetime.now(tz)
    print(f"Praegune aeg (Tallinn): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    for schedule in SCHEDULES:
        if should_record_now(schedule, now):
            print(f"Käivitan {schedule.name} otse-salvestuse!")
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
            
    print("Praegu ei ole ühtegi salvestamist vajavat saadet eetris.")

if __name__ == "__main__":
    main()
