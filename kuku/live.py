"""Otse-eetri salvestamise abifunktsioonid."""

from dataclasses import dataclass
from datetime import datetime

@dataclass
class Schedule:
    show_id: int
    name: str
    weekday: int
    hour: int
    duration_minutes: int


def get_ad_intervals(ad_times_str: str) -> list[tuple[int, int]]:
    """Tagastab reklaamide vahemikud sekundites."""
    if not ad_times_str:
        return []
        
    if ad_times_str.lower() == "auto":
        return [(0, 5 * 60), (30 * 60, 35 * 60)]
        
    intervals = []
    for part in ad_times_str.split(","):
        s, e = part.split("-")
        intervals.append((int(s) * 60, int(e) * 60))
    return intervals


def should_record_now(schedule: Schedule, now: datetime) -> bool:
    """Kontrollib, kas antud saate peaks praegu salvestama."""
    logical_hour = now.hour if now.minute < 30 else (now.hour + 1) % 24
    return now.weekday() == schedule.weekday and logical_hour == schedule.hour

import subprocess
import os
import tempfile
from pathlib import Path

def remove_ads(input_path: str, output_path: str, ad_intervals: list[tuple[int, int]]):
    # This expects total_duration to be known, but if we don't have it, we can just use a very large number for the end
    # For simplicity, let's keep track of segments to keep
    # e.g., if ads are (0, 300), (1800, 2100), then keep is (300, 1800) and (2100, 999999)
    keep_segments = []
    current_pos = 0
    for start, end in sorted(ad_intervals):
        if start > current_pos:
            keep_segments.append((current_pos, start))
        current_pos = max(current_pos, end)
    
    keep_segments.append((current_pos, 999999))
    
    if len(keep_segments) == 1 and keep_segments[0][0] == 0:
        # No ads to remove, just copy
        subprocess.run(["ffmpeg", "-y", "-i", input_path, "-c", "copy", output_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        part_files = []
        for i, (start, end) in enumerate(keep_segments):
            part = os.path.join(tmpdir, f"part{i}.mp3")
            part_files.append(part)
            subprocess.run([
                "ffmpeg", "-y", "-i", input_path, 
                "-ss", str(start), "-to", str(end),
                "-c", "copy", part
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        list_file = os.path.join(tmpdir, "list.txt")
        with open(list_file, "w") as f:
            for p in part_files:
                f.write(f"file '{p}'\n")
                
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, 
            "-c", "copy", output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)



import pytz
from kuku.api import Episode

def get_premiere_schedules(episodes: list[Episode], show_id: int, show_name: str) -> list[Schedule]:
    "Leiab API osade põhjal saate eetrisoleku ajad."
    tz = pytz.timezone('Europe/Tallinn')
    schedules = set()
    for ep in episodes[:5]:
        dt = ep.published_at.astimezone(tz)
        schedules.add((dt.weekday(), dt.hour))
    return [Schedule(show_id=show_id, name=show_name, weekday=w, hour=h, duration_minutes=60) for w, h in schedules]

