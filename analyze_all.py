import numpy as np
import scipy.signal
import subprocess
from pathlib import Path
from kuku.jingles import load_audio, SAMPLE_RATE, ASSETS_DIR, get_ffmpeg, _find_peaks

ffmpeg = get_ffmpeg()

start_tpl = load_audio(ASSETS_DIR / "puhas_alguskoll.wav")
st_zero = start_tpl - np.mean(start_tpl)
st_energy = np.sum(st_zero ** 2)

files = [
    ("Buum", "buum_start.mp3", 300),
    ("Digitund", "digitund_start.mp3", 300),
    ("Jaljed_gloobusel", "jaljed_start.mp3", 300)
]

for name, fname, base_sec in files:
    print(f"\n==================== {name} ({fname}) ====================")
    audio = load_audio(fname)
    dur = len(audio) / SAMPLE_RATE
    audio_sq = audio ** 2

    # Otsime reklaami alguskõlle
    c_start = scipy.signal.fftconvolve(audio, st_zero[::-1], mode="valid")
    o_start = np.ones(len(start_tpl))
    e_start = scipy.signal.fftconvolve(audio_sq, o_start, mode="valid")
    norm_start = c_start / np.sqrt(e_start * st_energy + 1e-6)
    p_start = _find_peaks(norm_start, SAMPLE_RATE, threshold=0.50, min_dist_sec=5.0)

    print("Reklaami alguskõllid (uudiste lõpp / reklaami algus):")
    for pos, sc in p_start:
        abs_t = base_sec + pos
        m, s = int(abs_t // 60), int(abs_t % 60)
        print(f"  Tipp: {m:02d}:{s:02d} ({abs_t:.1f}s, kohalik {pos:.1f}s) -> skoor: {sc:.4f}")

    # Otsime kõiki olemasolevaid lõpukõlle
    print("Vasted olemasolevate lõpukõllidega:")
    for f in sorted(ASSETS_DIR.glob("*.wav")):
        if f.name == "puhas_alguskoll.wav":
            continue
        t = load_audio(f)
        tz = t - np.mean(t)
        c = scipy.signal.fftconvolve(audio, tz[::-1], mode="valid")
        o = np.ones(len(t))
        e = scipy.signal.fftconvolve(audio_sq, o, mode="valid")
        nc = c / np.sqrt(e * np.sum(tz**2) + 1e-6)
        p = _find_peaks(nc, SAMPLE_RATE, threshold=0.45, min_dist_sec=5.0)
        for pos, sc in p:
            abs_t = base_sec + pos
            m, s = int(abs_t // 60), int(abs_t % 60)
            print(f"  {f.name:26s} Tipp: {m:02d}:{s:02d} ({abs_t:.1f}s) -> skoor: {sc:.4f}")
