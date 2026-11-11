import os
import urllib.request
import subprocess
import numpy as np
import scipy.signal
from pathlib import Path
from kuku.jingles import load_audio, SAMPLE_RATE, ASSETS_DIR, get_ffmpeg, _find_peaks

SHOWS = [
    {
        "id": 214,
        "name": "Buum",
        "url": "https://github.com/mssaar/kuku-raadio/releases/download/saade-214/raw-1794394802.mp3",
        "filename": "buum_start.mp3"
    },
    {
        "id": 209,
        "name": "Digitund",
        "url": "https://github.com/mssaar/kuku-raadio/releases/download/saade-209/raw-1794214801.mp3",
        "filename": "digitund_start.mp3"
    },
    {
        "id": 111513,
        "name": "Jaljed_gloobusel",
        "url": "https://github.com/mssaar/kuku-raadio/releases/download/saade-111513/raw-1793869202.mp3",
        "filename": "jaljed_start.mp3"
    }
]

# Tõmbame vahemiku 4:00 (240s) kuni 9:00 (540s)
# 1s = 16000 baiti
START_SEC = 240
END_SEC = 540
START_BYTE = START_SEC * 16000
END_BYTE = END_SEC * 16000 - 1

os.makedirs("recordings/audioklipid", exist_ok=True)

for show in SHOWS:
    fpath = show["filename"]
    if not os.path.exists(fpath) or os.path.getsize(fpath) < 1000000:
        print(f"Laadin alla {show['name']} vahemikku 4:00 - 9:00 ({START_BYTE}-{END_BYTE})...")
        req = urllib.request.Request(show["url"], headers={"Range": f"bytes={START_BYTE}-{END_BYTE}"})
        with urllib.request.urlopen(req) as resp, open(fpath, "wb") as f:
            f.write(resp.read())
        print(f"{show['name']} alla laaditud! ({os.path.getsize(fpath)} baiti)")
    else:
        print(f"{show['name']} toorfail on juba olemas ({os.path.getsize(fpath)} baiti).")
