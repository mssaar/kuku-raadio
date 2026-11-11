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


def detect_ad_intervals(audio_path: str | Path, assets_dir: Path = None, cut_start: bool = True, show_id: int | None = None) -> list[tuple[int, int]]:
    """Tuvastab helifailist reklaami alguskõllid ja lõpukõllid ning tagastab eemaldatavad intervallid.
    
    Kui show_id on antud ja saatele on olemas oma saatepõhised lõpukõllid (saade_{show_id}_lopukoll_*.wav),
    kasutatakse AINULT selle saate omi. Muul juhul otsitakse üldisest lõpukõllide kogust (puhas_lopukoll_*.wav).
    """
    assets = assets_dir or ASSETS_DIR
    start_tpl_path = assets / "puhas_alguskoll.wav"
    if not start_tpl_path.exists():
        print(f"Hoiatus: Etalonkõll {start_tpl_path} puudub!")
        fallback = [(0, 413), (1200, 1320), (2000, 2120), (2740, 2860), (3543, 3600)]
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

    # 2. Laeme lõpukõllide etalonid.
    # Kui saatele on sätestatud konkreetsed saatepõhised lõpukõllid (nt saade_{show_id}_lopukoll_*.wav),
    # siis arvestatakse AINULT neid. Muul juhul otsitakse üldisest hunnikust (puhas_lopukoll_*.wav).
    end_tpl_norms = []
    show_specific_templates = []
    if show_id is not None:
        show_specific_templates = sorted(assets.glob(f"saade_{show_id}_lopukoll_*.wav"))
        if not show_specific_templates:
            show_dir = assets / "shows" / str(show_id)
            if show_dir.exists():
                show_specific_templates = sorted(show_dir.glob("*.wav"))

    target_templates = show_specific_templates if show_specific_templates else sorted(assets.glob("puhas_lopukoll_*.wav"))

    for p in target_templates:
        t = load_audio(p, sr=SAMPLE_RATE)
        t_zero = t - np.mean(t)
        end_tpl_norms.append((t_zero, np.sum(t_zero ** 2), len(t) / SAMPLE_RATE))

    # 3. Saate alguse ja lõpu paika lõikamine tunnus-intro või vaikeaegade järgi:
    # Kui saatele on spetsiifiline tunnus-intro, otsitakse saate algust aknast [180s, 600s]
    # ja lõppu aknast [3300s, 3600s]. Muul juhul kasutatakse vaikeaegu (0-413s ja 3543s-lõpp).
    intervals: list[tuple[int, int]] = []
    start_cut_sec = 413
    if cut_start:
        if show_specific_templates and end_tpl_norms and audio_len_sec >= 180:
            intro_tpl, intro_energy, intro_dur = end_tpl_norms[0]
            search_start_idx = int(180 * SAMPLE_RATE)
            search_end_idx = min(len(audio), int(600 * SAMPLE_RATE))
            if search_end_idx - search_start_idx >= len(intro_tpl):
                win_audio = audio[search_start_idx:search_end_idx]
                win_sq = audio_sq[search_start_idx:search_end_idx]
                c_intro = scipy.signal.fftconvolve(win_audio, intro_tpl[::-1], mode="valid")
                o_intro = np.ones(len(intro_tpl))
                e_intro = scipy.signal.fftconvolve(win_sq, o_intro, mode="valid")
                norm_intro = c_intro / np.sqrt(e_intro * intro_energy + 1e-6)
                intro_peaks = _find_peaks(norm_intro, SAMPLE_RATE, threshold=0.65, min_dist_sec=5.0)
                if intro_peaks:
                    best_intro = max(intro_peaks, key=lambda x: x[1])
                    start_cut_sec = int(round(180.0 + best_intro[0] + intro_dur))
        intervals.append((0, start_cut_sec))

    end_cut_sec = 3543
    if show_specific_templates and end_tpl_norms and audio_len_sec >= 3300:
        intro_tpl, intro_energy, intro_dur = end_tpl_norms[0]
        search_outro_start_idx = int(3300 * SAMPLE_RATE)
        search_outro_end_idx = min(len(audio), int(3600 * SAMPLE_RATE))
        if search_outro_end_idx - search_outro_start_idx >= len(intro_tpl):
            win_audio = audio[search_outro_start_idx:search_outro_end_idx]
            win_sq = audio_sq[search_outro_start_idx:search_outro_end_idx]
            c_outro = scipy.signal.fftconvolve(win_audio, intro_tpl[::-1], mode="valid")
            o_outro = np.ones(len(intro_tpl))
            e_outro = scipy.signal.fftconvolve(win_sq, o_outro, mode="valid")
            norm_outro = c_outro / np.sqrt(e_outro * intro_energy + 1e-6)
            outro_peaks = _find_peaks(norm_outro, SAMPLE_RATE, threshold=0.65, min_dist_sec=5.0)
            if outro_peaks:
                best_outro = max(outro_peaks, key=lambda x: x[1])
                outro_time = 3300.0 + best_outro[0]
                outro_duration = max(intro_dur, 12.0)
                end_cut_sec = int(round(outro_time + outro_duration))

    min_mid_start = start_cut_sec if cut_start else 0
    mid_show_starts = [p for p in all_start_peaks if min_mid_start <= p[0] <= end_cut_sec]

    for start_sec, sim in mid_show_starts:
        # Otsime lõpukõlli aknast [start_sec + 60s, start_sec + 270s] (reklaamipausid võivad kesta kuni 4,5 min)
        search_start = int((start_sec + 60) * SAMPLE_RATE)
        search_end = min(len(audio), int((start_sec + 270) * SAMPLE_RATE))
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

    # Lõpu kärpimine (ainult siis, kui salvestus ulatub üle tuvastatud saate lõpu)
    if audio_len_sec > end_cut_sec:
        intervals.append((end_cut_sec, int(round(audio_len_sec))))
    return sorted(intervals)
