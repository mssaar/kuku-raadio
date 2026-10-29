"""Raadio Kuku reklaamikõllide akustiline tuvastaja."""

import os
import shutil
import subprocess
from pathlib import Path
import numpy as np
import scipy.signal

SAMPLE_RATE = 8000
ASSETS_DIR = Path(__file__).parent / "assets"


def get_ffmpeg() -> str:
    """Tagastab süsteemi ffmpeg käsu või imageio_ffmpeg binaari."""
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def load_audio(path: str | Path, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Laeb helifaili mono float32 massiivina etteantud diskreetimissagedusel."""
    ffmpeg = get_ffmpeg()
    cmd = [
        ffmpeg, "-y",
        "-i", str(path),
        "-ac", "1",
        "-ar", str(sr),
        "-f", "s16le",
        "-"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
    return np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32)


def _find_peaks(norm_corr: np.ndarray, sr: int, threshold: float = 0.65, min_dist_sec: float = 10.0) -> list[tuple[float, float]]:
    above = np.where(norm_corr >= threshold)[0]
    peaks = []
    if len(above) > 0:
        cur = [above[0]]
        min_samples = int(sr * min_dist_sec)
        for idx in above[1:]:
            if idx - cur[-1] < min_samples:
                cur.append(idx)
            else:
                best = max(cur, key=lambda i: norm_corr[i])
                peaks.append(best)
                cur = [idx]
        if cur:
            best = max(cur, key=lambda i: norm_corr[i])
            peaks.append(best)
    return [(idx / sr, float(norm_corr[idx])) for idx in peaks]


def detect_ad_intervals(audio_path: str | Path, assets_dir: Path = None, cut_start: bool = True) -> list[tuple[int, int]]:
    """Tuvastab helifailist reklaami alguskõllid ja lõpukõllid ning tagastab eemaldatavad intervallid."""
    assets = assets_dir or ASSETS_DIR
    start_tpl_path = assets / "puhas_alguskoll.wav"
    if not start_tpl_path.exists():
        print(f"Hoiatus: Etalonkõll {start_tpl_path} puudub!")
        fallback = [(0, 413), (1200, 1320), (2000, 2120), (2740, 2860), (3463, 3600)]
        if not cut_start:
            fallback = [(s, e) for s, e in fallback if s > 0]
        return fallback

    audio = load_audio(audio_path, sr=SAMPLE_RATE)
    audio_len_sec = len(audio) / SAMPLE_RATE

    start_tpl = load_audio(start_tpl_path, sr=SAMPLE_RATE)
    start_tpl = start_tpl - np.mean(start_tpl)
    start_energy = np.sum(start_tpl ** 2)

    # 1. Tuvastame alguskõllid üle terve saate
    corr_start = scipy.signal.fftconvolve(audio, start_tpl[::-1], mode="valid")
    audio_sq = audio ** 2
    ones_start = np.ones(len(start_tpl))
    energy_start = scipy.signal.fftconvolve(audio_sq, ones_start, mode="valid")
    norm_corr_start = corr_start / np.sqrt(energy_start * start_energy + 1e-6)

    all_start_peaks = _find_peaks(norm_corr_start, SAMPLE_RATE, threshold=0.70, min_dist_sec=10.0)

    # Laeme lõpukõllide etalonid
    end_tpl_norms = []
    for i in [1, 2, 3]:
        p = assets / f"puhas_lopukoll_{i}.wav"
        if p.exists():
            t = load_audio(p, sr=SAMPLE_RATE)
            t_zero = t - np.mean(t)
            end_tpl_norms.append((t_zero, np.sum(t_zero ** 2), len(t) / SAMPLE_RATE))

    # Reegel:
    # 1. 0:00 - 6:53 (413s, 5s varuga) lõigatakse ainult siis, kui cut_start on tõene (täistunnil alustades)
    # 2. 57:43 (3463s) kuni saate lõpp lõigatakse ainult siis, kui fail on piisavalt pikk
    # 3. Vahepausid on need, mis jäävad alguse ja lõpu vahele
    min_mid_start = 413 if cut_start else 0
    mid_show_starts = [p for p in all_start_peaks if min_mid_start <= p[0] <= 3463]

    intervals: list[tuple[int, int]] = []
    if cut_start:
        intervals.append((0, 413))

    for start_sec, sim in mid_show_starts:
        # Otsime lõpukõlli aknast [start_sec + 60s, start_sec + 160s]
        search_start = int((start_sec + 60) * SAMPLE_RATE)
        search_end = min(len(audio), int((start_sec + 160) * SAMPLE_RATE))
        window_audio = audio[search_start:search_end]
        window_sq = audio_sq[search_start:search_end]

        best_end_sec = None
        best_end_score = 0
        best_tpl_len = 4.0

        for tpl_end, tpl_e, tpl_dur in end_tpl_norms:
            c_end = scipy.signal.fftconvolve(window_audio, tpl_end[::-1], mode="valid")
            o_end = np.ones(len(tpl_end))
            e_end = scipy.signal.fftconvolve(window_sq, o_end, mode="valid")
            norm_end = c_end / np.sqrt(e_end * tpl_e + 1e-6)
            end_peaks = _find_peaks(norm_end, SAMPLE_RATE, threshold=0.60, min_dist_sec=5.0)
            for p_offset, score in end_peaks:
                if score > best_end_score:
                    best_end_score = score
                    best_end_sec = (start_sec + 60) + p_offset
                    best_tpl_len = tpl_dur

        if best_end_sec is not None and best_end_score >= 0.60:
            end_time = int(round(best_end_sec + best_tpl_len))
        else:
            # Fallback: tavapärane 90s reklaamipaus
            end_time = int(round(start_sec + 90))

        intervals.append((int(round(start_sec)), end_time))

    # Lõpu kärpimine (ainult siis, kui salvestus ulatub saate lõpuni)
    if audio_len_sec > 3463:
        intervals.append((3463, int(round(audio_len_sec))))
    return sorted(intervals)
