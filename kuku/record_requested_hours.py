"""Salvestab Kuku otse-eetrist toorheli kahel järjestikusel täistunnil (12:00-13:00 ja 13:00-14:00)."""

import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
import pytz

STREAM_URL = "https://router.euddn.net/8103046e16b71d15d692b57c187875c7/kuku.mp3"
LOG_FILE = Path("recordings") / "recorder.log"


def log(msg: str):
    tz = pytz.timezone("Europe/Tallinn")
    ts = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def record_stream_to_file(output_path: Path, duration_seconds: int):
    """Salvestab etteantud sekundid otsevoogu faili."""
    req = urllib.request.Request(STREAM_URL, headers={"User-Agent": "Mozilla/5.0"})
    t0 = time.time()
    last_log = t0
    bytes_written = 0

    with open(output_path, "wb") as f:
        while time.time() - t0 < duration_seconds:
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    while time.time() - t0 < duration_seconds:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_written += len(chunk)
                        now_t = time.time()
                        if now_t - last_log >= 300:  # logi iga 5 min tagant
                            elapsed = int(now_t - t0)
                            mb = bytes_written / (1024 * 1024)
                            log(f"Salvestatud {elapsed}/{duration_seconds}s ({mb:.1f} MB)...")
                            last_log = now_t
            except Exception as e:
                log(f"Hoiatus voo katkemisel: {e}. Taastame ühenduse 3 sekundi pärast...")
                time.sleep(3)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    log(f"Salvestus valmis: {output_path.name} ({size_mb:.1f} MB, {duration_seconds}s)")


def wait_until(target_dt: datetime):
    tz = pytz.timezone("Europe/Tallinn")
    while True:
        now = datetime.now(tz)
        diff = (target_dt - now).total_seconds()
        if diff <= 0.5:
            break
        if diff > 60:
            log(f"Ootan kella {target_dt.strftime('%H:%M:%S')} (jäänud {int(diff // 60)}m {int(diff % 60)}s)...")
            sleep_time = min(60.0, diff - 10)
        else:
            sleep_time = max(0.1, min(1.0, diff))
        time.sleep(sleep_time)


def main():
    tz = pytz.timezone("Europe/Tallinn")
    now = datetime.now(tz)
    rec_dir = Path("recordings")
    rec_dir.mkdir(exist_ok=True)

    log("Kuku raadio täistundide toorsalvestaja käivitus.")

    # 1. Täistund: 12:00 - 13:00
    target_12 = now.replace(hour=12, minute=0, second=0, microsecond=0)
    out_12 = rec_dir / "kuku_2026-10-22_12-00_toorheli.mp3"

    if now < target_12:
        log(f"Esimene sihtmärk: 12:00:00 (fail: {out_12.name})")
        wait_until(target_12)
        log("Kell on 12:00:00! Alustan 12:00-13:00 toorheli salvestamist...")
        record_stream_to_file(out_12, 3600)
    elif now < target_12 + timedelta(hours=1):
        rem = int((target_12 + timedelta(hours=1) - now).total_seconds())
        log(f"Kell on juba vahemikus 12:00-13:00. Salvestan ülejäänud {rem} sekundit...")
        record_stream_to_file(out_12, rem)
    else:
        log("Kella 12:00 tund on juba möödas.")

    # 2. Täistund: 13:00 - 14:00
    now = datetime.now(tz)
    target_13 = now.replace(hour=13, minute=0, second=0, microsecond=0)
    out_13 = rec_dir / "kuku_2026-10-22_13-00_toorheli.mp3"

    if now < target_13:
        log(f"Teine sihtmärk: 13:00:00 (fail: {out_13.name})")
        wait_until(target_13)
        log("Kell on 13:00:00! Alustan 13:00-14:00 toorheli salvestamist...")
        record_stream_to_file(out_13, 3600)
    elif now < target_13 + timedelta(hours=1):
        rem = int((target_13 + timedelta(hours=1) - now).total_seconds())
        log(f"Kell on vahemikus 13:00-14:00. Salvestan ülejäänud {rem} sekundit...")
        record_stream_to_file(out_13, rem)
    else:
        log("Kella 13:00 tund on juba möödas.")

    log("Kõik soovitud täistunnid (12:00-13:00 ja 13:00-14:00) on edukalt salvestatud!")


if __name__ == "__main__":
    main()
