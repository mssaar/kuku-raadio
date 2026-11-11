import numpy as np
import subprocess
from kuku.jingles import load_audio, SAMPLE_RATE, get_ffmpeg

ffmpeg = get_ffmpeg()

# 1. BUUM: reklaam algas kell 327s (05:27).
# Uurime aega 380s kuni 480s (kohalik 80s kuni 180s failis buum_start.mp3)
print("=== BUUM ülemineku otsing ===")
audio_buum = load_audio("buum_start.mp3")
# Otsime helitaseme muutust (reklaami lõpusõnad -> mikrosilm -> tunnusmuusika)
for s in range(60, min(180, int(len(audio_buum)/SAMPLE_RATE))):
    chunk = audio_buum[int(s*SAMPLE_RATE):int((s+1)*SAMPLE_RATE)]
    rms = np.sqrt(np.mean(chunk**2))
    abs_t = 300 + s
    m, sec = int(abs_t // 60), int(abs_t % 60)
    if rms < 3000: # Vaikus või paus
        print(f"  VAIKUS / PAUS: {m:02d}:{sec:02d} (abs {abs_t}s, kohalik {s}s): rms={rms:.1f}")

# 2. JÄLJED GLOOBUSEL: reklaam algas kell 305s (05:05).
print("\n=== JÄLJED GLOOBUSEL ülemineku otsing ===")
audio_jaljed = load_audio("jaljed_start.mp3")
for s in range(50, min(180, int(len(audio_jaljed)/SAMPLE_RATE))):
    chunk = audio_jaljed[int(s*SAMPLE_RATE):int((s+1)*SAMPLE_RATE)]
    rms = np.sqrt(np.mean(chunk**2))
    abs_t = 300 + s
    m, sec = int(abs_t // 60), int(abs_t % 60)
    if rms < 3000:
        print(f"  VAIKUS / PAUS: {m:02d}:{sec:02d} (abs {abs_t}s, kohalik {s}s): rms={rms:.1f}")
