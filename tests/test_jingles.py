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
    assert intervals == [(0, 413), (1200, 1320), (2000, 2120), (2740, 2860), (3543, 3600)]

    intervals_no_cut = detect_ad_intervals(fake_audio, assets_dir=empty_dir, cut_start=False)
    assert intervals_no_cut == [(1200, 1320), (2000, 2120), (2740, 2860), (3543, 3600)]


def test_assets_contain_all_jingles():
    from kuku.jingles import ASSETS_DIR
    wavs = list(ASSETS_DIR.glob("puhas_lopukoll_*.wav"))
    assert len(wavs) >= 6
    # Tarkade Klubi (231) saatepõhine kõll
    tk_wavs = list(ASSETS_DIR.glob("saade_231_lopukoll_*.wav"))
    assert len(tk_wavs) >= 1


def test_detect_ad_intervals_uses_show_specific_template(tmp_path, monkeypatch):
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "puhas_alguskoll.wav").write_bytes(b"dummy")
    (assets_dir / "puhas_lopukoll_1.wav").write_bytes(b"dummy")
    (assets_dir / "saade_231_lopukoll_1.wav").write_bytes(b"dummy")

    fake_audio = tmp_path / "test.mp3"
    fake_audio.write_bytes(b"audio")

    loaded_paths = []

    def mock_load(path, sr=8000):
        loaded_paths.append(Path(path).name)
        # Return 1 second of silence
        return np.zeros(sr, dtype=np.float32)

    monkeypatch.setattr("kuku.jingles.load_audio", mock_load)

    # 1. show_id=231 puhul peab laadima AINULT saade_231_lopukoll_1.wav ja MITTE puhas_lopukoll_1.wav
    loaded_paths.clear()
    detect_ad_intervals(fake_audio, assets_dir=assets_dir, show_id=231)
    assert "saade_231_lopukoll_1.wav" in loaded_paths
    assert "puhas_lopukoll_1.wav" not in loaded_paths

    # 2. Saate puhul, millel pole oma kõlli (nt show_id=999 või None), laaditakse üldine hunnik (puhas_lopukoll_1.wav)
    loaded_paths.clear()
    detect_ad_intervals(fake_audio, assets_dir=assets_dir, show_id=999)
    assert "puhas_lopukoll_1.wav" in loaded_paths
    assert "saade_231_lopukoll_1.wav" not in loaded_paths

    loaded_paths.clear()
    detect_ad_intervals(fake_audio, assets_dir=assets_dir, show_id=None)
    assert "puhas_lopukoll_1.wav" in loaded_paths
    assert "saade_231_lopukoll_1.wav" not in loaded_paths


