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
    # Kõigi 4 saate saatepõhised tunnus-introd
    assert len(list(ASSETS_DIR.glob("saade_231_lopukoll_*.wav"))) >= 1  # Tarkade Klubi
    assert len(list(ASSETS_DIR.glob("saade_209_lopukoll_*.wav"))) >= 1  # Digitund
    assert len(list(ASSETS_DIR.glob("saade_214_lopukoll_*.wav"))) >= 1  # Buum
    assert len(list(ASSETS_DIR.glob("saade_111513_lopukoll_*.wav"))) >= 1  # Jäljed gloobusel


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


def test_detect_ad_intervals_cuts_start_and_end_by_theme_intro(tmp_path, monkeypatch):
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "puhas_alguskoll.wav").write_bytes(b"dummy")
    (assets_dir / "saade_231_lopukoll_1.wav").write_bytes(b"dummy")

    fake_audio = tmp_path / "test.mp3"
    fake_audio.write_bytes(b"audio")

    sr = 1000  # kiirendatud diskreetimissagedus testimiseks
    monkeypatch.setattr("kuku.jingles.SAMPLE_RATE", sr)

    # Loome simuleeritud 3600s heli ja 6s pikkuse tunnusheli
    intro_dur_sec = 6
    np.random.seed(42)
    intro_wave = np.random.randn(sr * intro_dur_sec).astype(np.float32)
    start_jingle_wave = np.random.randn(sr * 3).astype(np.float32)

    total_len = sr * 3600
    full_audio = np.random.randn(total_len).astype(np.float32) * 0.05
    # Paigutame tunnus-intro algusesse (t=460s) ja lõppu (t=3580s)
    full_audio[460 * sr : 460 * sr + len(intro_wave)] += intro_wave * 5.0
    full_audio[3580 * sr : 3580 * sr + len(intro_wave)] += intro_wave * 5.0

    def mock_load(path, sr=sr):
        p = Path(path).name
        if p == "saade_231_lopukoll_1.wav":
            return intro_wave
        if p == "puhas_alguskoll.wav":
            return start_jingle_wave
        return full_audio

    monkeypatch.setattr("kuku.jingles.load_audio", mock_load)

    # 1. show_id=231 puhul lõikab alguse 460s pealt ja lõpu 3580 + 12 = 3592s pealt
    intervals = detect_ad_intervals(fake_audio, assets_dir=assets_dir, cut_start=True, show_id=231)
    assert intervals[0] == (0, 460)
    assert intervals[-1] == (3592, 3600)

    # 2. cut_start=False puhul algust ei lõigata (ei lisata (0, 460))
    intervals_no_cut = detect_ad_intervals(fake_audio, assets_dir=assets_dir, cut_start=False, show_id=231)
    assert intervals_no_cut[0] != (0, 460)
    assert intervals_no_cut[-1] == (3592, 3600)



