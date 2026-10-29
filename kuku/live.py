"""Otse-eetri salvestamise abifunktsioonid."""

import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import pytz

from kuku.api import Episode

# Vaikimisi varuintervallid, kui helifaili pole antud või automaattuvastus ei käivitu:
# 1. 0:00 - 6:53 (alguse uudised ja reklaamid: 0 - 413 s, 5s varuga enne saadet)
# 2. 20:28 - 21:42 (1. reklaamipaus: 1228 - 1302 s)
# 3. 33:10 - 34:49 (2. reklaamipaus: 1990 - 2089 s)
# 4. 45:44 - 47:54 (3. reklaamipaus: 2744 - 2874 s)
# 5. 57:43 - 60:00 (lõpukõll ja järgmise tunni algus: 3463 - 3600 s)
DEFAULT_AUTO_INTERVALS = [(0, 413), (1228, 1302), (1990, 2089), (2744, 2874), (3463, 3600)]


@dataclass
class Schedule:
    show_id: int
    name: str
    weekday: int
    hour: int
    duration_minutes: int


def parse_time_seconds(time_str: str) -> int:
    """Teisendab aja stringi (nt '11:10', '1:55', '5') sekunditeks."""
    time_str = time_str.strip()
    if ":" in time_str:
        parts = time_str.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return int(time_str) * 60


def get_ad_intervals(ad_times_str: str, audio_path: str | Path = None, cut_start: bool = True) -> list[tuple[int, int]]:
    """Tagastab reklaamide vahemikud sekundites.
    
    Kui ad_times_str on 'auto' ja audio_path on antud, tuvastatakse intervallid
    akustiliselt reklaamikõllide järgi.
    """
    if not ad_times_str:
        return []

    if ad_times_str.lower() == "auto":
        if audio_path and os.path.exists(audio_path):
            try:
                from kuku.jingles import detect_ad_intervals
                detected = detect_ad_intervals(audio_path, cut_start=cut_start)
                if detected:
                    return detected
            except Exception as e:
                print(f"Hoiatus: Akustiline kõllituvastus ebaõnnestus: {e}, kasutan vaikeaegu.")
        if not cut_start:
            return [(s, e) for s, e in DEFAULT_AUTO_INTERVALS if s > 0]
        return list(DEFAULT_AUTO_INTERVALS)

    intervals = []
    for part in ad_times_str.split(","):
        s, e = part.split("-")
        intervals.append((parse_time_seconds(s), parse_time_seconds(e)))
    return intervals


def should_record_now(schedule: Schedule, now: datetime) -> bool:
    """Kontrollib, kas antud saate peaks praegu (või kohe saabuval täistunnil) salvestama."""
    target = (now + timedelta(minutes=30)) if now.minute >= 30 else now
    return target.weekday() == schedule.weekday and target.hour == schedule.hour


def compute_recording_plan(schedule: Schedule, now: datetime) -> tuple[int, int]:
    """Tagastab (ootamise_sekundid, salvestuse_kestus_minutites)."""
    if now.minute >= 30:
        wait_seconds = (60 - now.minute) * 60 - now.second
        return wait_seconds, schedule.duration_minutes
    remaining_minutes = max(1, schedule.duration_minutes - now.minute)
    return 0, remaining_minutes


def remove_ads(input_path: str, output_path: str, ad_intervals: list[tuple[int, int]]):
    from kuku.jingles import get_ffmpeg
    ffmpeg = get_ffmpeg()

    keep_segments = []
    current_pos = 0
    for start, end in sorted(ad_intervals):
        if start > current_pos:
            keep_segments.append((current_pos, start))
        current_pos = max(current_pos, end)

    keep_segments.append((current_pos, 999999))

    if len(keep_segments) == 1 and keep_segments[0][0] == 0:
        subprocess.run([ffmpeg, "-y", "-i", input_path, "-c", "copy", output_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        part_files = []
        for i, (start, end) in enumerate(keep_segments):
            part = os.path.join(tmpdir, f"part{i}.mp3")
            part_files.append(part)
            subprocess.run([
                ffmpeg, "-y", "-i", input_path,
                "-ss", str(start), "-to", str(end),
                "-c", "copy", part
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        list_file = os.path.join(tmpdir, "list.txt")
        with open(list_file, "w") as f:
            for p in part_files:
                f.write(f"file '{p}'\n")

        subprocess.run([
            ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_file,
            "-c", "copy", output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def get_premiere_schedules(episodes: list[Episode], show_id: int, show_name: str) -> list[Schedule]:
    """Leiab API osade põhjal saate eetrisoleku ajad."""
    tz = pytz.timezone('Europe/Tallinn')
    schedules = set()
    for ep in episodes[:5]:
        dt = ep.published_at.astimezone(tz)
        schedules.add((dt.weekday(), dt.hour))
    return [Schedule(show_id=show_id, name=show_name, weekday=w, hour=h, duration_minutes=60) for w, h in schedules]
