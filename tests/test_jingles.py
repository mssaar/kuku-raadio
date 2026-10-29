import numpy as np
import pytest
from pathlib import Path
from kuku.jingles import _find_peaks, get_ffmpeg, detect_ad_intervals


def test_get_ffmpeg():
    cmd = get_ffmpeg()
    assert isinstance(cmd, str)
    assert len(cmd) > 0


def test_find_peaks():
    sr = 1000
    # Simulate a signal with 2 clear peaks
    arr = np.zeros(sr * 30, dtype=np.float32)
    arr[int(5 * sr)] = 0.95
    arr[int(20 * sr)] = 0.88

    peaks = _find_peaks(arr, sr, threshold=0.70, min_dist_sec=5.0)
    assert len(peaks) == 2
    assert abs(peaks[0][0] - 5.0) < 0.01
    assert abs(peaks[1][0] - 20.0) < 0.01


def test_detect_ad_intervals_missing_assets(tmp_path):
    empty_dir = tmp_path / "empty_assets"
    empty_dir.mkdir()
    fake_audio = tmp_path / "fake.mp3"
    fake_audio.write_bytes(b"dummy")

    intervals = detect_ad_intervals(fake_audio, assets_dir=empty_dir)
    assert intervals == [(0, 413), (1200, 1320), (2000, 2120), (2740, 2860), (3463, 3600)]

    intervals_no_cut = detect_ad_intervals(fake_audio, assets_dir=empty_dir, cut_start=False)
    assert intervals_no_cut == [(1200, 1320), (2000, 2120), (2740, 2860), (3463, 3600)]
