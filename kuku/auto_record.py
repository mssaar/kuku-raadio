"""Automaatne Kuku saadete otse-eetrist salvestaja (käivitatakse cron-ist)."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
import pytz

from kuku.live import Schedule, should_record_now, compute_recording_plan, get_premiere_schedules
from kuku.api import KukuClient
from kuku.sync import DATA_DIR


def _wait_seconds_for_time_str(now: datetime, hhmm: str) -> int:
    """Arvutab ootamise sekundid kellaajani HH:MM (Tallinna aeg)."""
    if not hhmm or ":" not in hhmm:
        return 0
    parts = hhmm.strip().split(":")
    target = now.replace(hour=int(parts[0]), minute=int(parts[1]), second=0, microsecond=0)
    if target < now:
        diff = (now - target).total_seconds()
        if diff > 12 * 3600:
            target += timedelta(days=1)
        else:
            return 0
    wait_sec = int((target - now).total_seconds())
    return wait_sec if 0 < wait_sec <= 3600 else 0


def main(now_override: datetime | None = None):
    tz = pytz.timezone("Europe/Tallinn")
    now = now_override or datetime.now(tz)
    print(f"Praegune aeg (Tallinn): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    shows_file = DATA_DIR / "shows.json"
    if not shows_file.exists():
        print("shows.json puudub!")
        return

    with open(shows_file, "r", encoding="utf-8") as f:
        my_shows = json.load(f)

    test_minutes_str = os.environ.get("TEST_RECORD_MINUTES", "").strip()
    if test_minutes_str:
        test_minutes = int(test_minutes_str)
        start_time_str = os.environ.get("TEST_START_TIME", "").strip()
        wait_sec = _wait_seconds_for_time_str(now, start_time_str)
        if wait_sec > 0:
            print(f"Testrežiim: ootan {wait_sec} sekundit kuni kellaajani {start_time_str}...")
            time.sleep(wait_sec)
            now = now + timedelta(seconds=wait_sec)

        first_show = my_shows[0] if my_shows else {"id": 209, "name": "Digitund"}
        title = f"{first_show['name']} (Test {now.strftime('%d.%m.%Y %H:%M')})"
        print(f"Käivitan {test_minutes}-minutilise testsalvestuse: {title}")
        cmd = [
            sys.executable, "-m", "kuku.record_live",
            "--show-id", str(first_show["id"]),
            "--show-name", first_show["name"],
            "--episode-title", title,
            "--duration", str(test_minutes),
            "--ad-times", ""
        ]
        subprocess.run(cmd, check=True)
        return

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
                    wait_sec, duration_min = compute_recording_plan(schedule, now)
                    if wait_sec > 0:
                        print(f"Saade '{schedule.name}' algab täistunnil {schedule.hour:02d}:00. Ootan {wait_sec} sekundit...")
                        time.sleep(wait_sec)
                        now = now + timedelta(seconds=wait_sec)
                    print(f"Käivitan '{schedule.name}' otse-salvestuse ({duration_min} min)!")
                    cmd = [
                        sys.executable, "-m", "kuku.record_live",
                        "--show-id", str(schedule.show_id),
                        "--show-name", schedule.name,
                        "--episode-title", f"{schedule.name} ({now.strftime('%d.%m.%Y')})",
                        "--duration", str(duration_min),
                        "--ad-times", "auto"
                    ]
                    subprocess.run(cmd, check=True)
                    return  # Salvestame korraga ühe (esimese mis klapib)
        except Exception as e:
            print(f"Viga saate '{show_name}' laadimisel: {e}")

    print("Praegu ei ole ühtegi salvestamist vajavat saadet eetris.")


if __name__ == "__main__":
    main()

