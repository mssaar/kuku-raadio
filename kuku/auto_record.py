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

    # Kustutame vana 10-min Digitunni test-asseti, kui see on GitHubis alles
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if repo and token:
        try:
            from kuku.releases import GitHubClient
            gh = GitHubClient(repo, token)
            rel = gh.find_release("saade-209")
            if rel:
                assets = gh.list_assets(rel)
                if "1792131850.mp3" in assets:
                    gh.delete_asset(assets["1792131850.mp3"]["id"])
                    print("Kustutasin vana 10-min Digitunni testfaili GitHubist.")
        except Exception as e:
            print(f"Hoiatus vana testfaili kustutamisel: {e}")

    library_file = DATA_DIR / "library.json"
    library = {"shows": []}
    if library_file.exists():
        with open(library_file, "r", encoding="utf-8") as f:
            library = json.load(f)

    # Kui shows.json sisaldab reaalaja-testi kirjet (live_only), millel pole veel salvestust,
    # salvestame kohe praegusel ajahetkel 5 minutit Kuku Raadio otse-eetrit.
    for show in my_shows:
        if show.get("live_only"):
            existing_eps = next(
                (s.get("episodes", []) for s in library.get("shows", []) if s["id"] == show["id"]),
                [],
            )
            if not existing_eps:
                duration_min = int(show.get("duration_minutes", 5))
                end_dt = now + timedelta(minutes=duration_min)
                title = f"Kuku otse-eeter reaalajas ({now.strftime('%d.%m.%Y %H:%M')}–{end_dt.strftime('%H:%M')})"
                print(f"Käivitan {duration_min}-minutilise reaalaja otse-eetri salvestuse: {title}")
                cmd = [
                    sys.executable, "-m", "kuku.record_live",
                    "--show-id", str(show["id"]),
                    "--show-name", show["name"],
                    "--episode-title", title,
                    "--duration", str(duration_min),
                    "--ad-times", ""
                ]
                subprocess.run(cmd, check=True)
                return

    client = KukuClient()
    since = datetime.now(timezone.utc) - timedelta(days=60)

    for show in my_shows:
        if show.get("live_only"):
            continue
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
                    is_mid_show = (wait_sec == 0 and now.minute >= 2)
                    print(f"Käivitan '{schedule.name}' otse-salvestuse ({duration_min} min, poole pealt={is_mid_show})!")
                    cmd = [
                        sys.executable, "-m", "kuku.record_live",
                        "--show-id", str(schedule.show_id),
                        "--show-name", schedule.name,
                        "--episode-title", f"{schedule.name} ({now.strftime('%d.%m.%Y')})",
                        "--duration", str(duration_min),
                        "--ad-times", "auto"
                    ]
                    if is_mid_show:
                        cmd.append("--no-cut-start")
                    subprocess.run(cmd, check=True)
                    return  # Salvestame korraga ühe (esimese mis klapib)
        except Exception as e:
            print(f"Viga saate '{show_name}' laadimisel: {e}")

    print("Praegu ei ole ühtegi salvestamist vajavat saadet eetris.")


if __name__ == "__main__":
    main()

