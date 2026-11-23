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
    import wave
    from kuku.jingles import ASSETS_DIR
    wavs = list(ASSETS_DIR.glob("puhas_lopukoll_*.wav"))
    assert len(wavs) >= 6
    # Kõigi 4 saate saatepõhised täispikad tunnus-introd (>= 8s)
    for sid in (231, 209, 214, 111513):
        matches = list(ASSETS_DIR.glob(f"saade_{sid}_lopukoll_*.wav"))
        assert len(matches) >= 1
        with wave.open(str(matches[0]), "rb") as w:
            dur = w.getnframes() / w.getframerate()
        assert dur >= 8.0, f"Saate {sid} tunnus-intro on liiga lühike ({dur:.2f}s)"
    # Sponsorikõllid saadetele, millel on sponsori bumber vahetult pärast introt
    for sid in (231, 209, 214):
        assert len(list(ASSETS_DIR.glob(f"saade_{sid}_sponsor_*.wav"))) >= 1


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

    # 1. show_id=231 puhul lõikab alguse koos tunnus-introga (460 + 6 = 466s) ja lõpu 3580 + 12 = 3592s pealt
    intervals = detect_ad_intervals(fake_audio, assets_dir=assets_dir, cut_start=True, show_id=231)
    assert intervals[0] == (0, 466)
    assert intervals[-1] == (3592, 3600)

    # 2. cut_start=False puhul algust ei lõigata (ei lisata (0, 466))
    intervals_no_cut = detect_ad_intervals(fake_audio, assets_dir=assets_dir, cut_start=False, show_id=231)
    assert intervals_no_cut[0] != (0, 466)
    assert intervals_no_cut[-1] == (3592, 3600)


def test_detect_ad_intervals_robust_to_mid_jingle_stream_jitter(tmp_path, monkeypatch):
    """Otse-eetri voos võib pika (9s) tunnus-intro keskel olla ~6ms ajaline hüpe; tuvastus ei tohi selle peale katkeda."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "puhas_alguskoll.wav").write_bytes(b"dummy")
    (assets_dir / "saade_111513_lopukoll_1.wav").write_bytes(b"dummy")

    fake_audio = tmp_path / "test.mp3"
    fake_audio.write_bytes(b"audio")

    sr = 1000
    monkeypatch.setattr("kuku.jingles.SAMPLE_RATE", sr)

    rng = np.random.default_rng(123)
    intro_wave = rng.standard_normal(sr * 9).astype(np.float32)
    start_jingle_wave = rng.standard_normal(sr * 3).astype(np.float32)

    # Lisame 6ms (6 sämplit) hüppe täpselt intro keskele (t=4.5s), nagu Jäljed gloobusel 19.11 vs 12.11
    half = len(intro_wave) // 2
    jittered_intro = np.concatenate([intro_wave[:half], np.zeros(6, dtype=np.float32), intro_wave[half:]])

    full_audio = rng.standard_normal(sr * 3600).astype(np.float32) * 0.05
    # Saate alguse intro (t=440s) + üks keskmine reklaamipaus (algus 1120s, lõpp-intro 1240s)
    full_audio[440 * sr : 440 * sr + len(jittered_intro)] += jittered_intro * 5.0
    full_audio[1120 * sr : 1120 * sr + len(start_jingle_wave)] += start_jingle_wave * 5.0
    full_audio[1240 * sr : 1240 * sr + len(jittered_intro)] += jittered_intro * 5.0

    def mock_load(path, sr=sr):
        p = Path(path).name
        if p == "saade_111513_lopukoll_1.wav":
            return intro_wave
        if p == "puhas_alguskoll.wav":
            return start_jingle_wave
        return full_audio

    monkeypatch.setattr("kuku.jingles.load_audio", mock_load)

    intervals = detect_ad_intervals(fake_audio, assets_dir=assets_dir, cut_start=True, show_id=111513)
    # Peab tuvastama algus-intro (440 + 9 = 449s), mitte langema vaikeajale 413s
    assert intervals[0][0] == 0
    assert 448 <= intervals[0][1] <= 450
    # Peab tuvastama keskmise reklaamipausi lõpu (1240 + 9 = 1249s), mitte +90s fallback (1210s)
    mid = [iv for iv in intervals if 1118 <= iv[0] <= 1122]
    assert len(mid) == 1
    assert 1248 <= mid[0][1] <= 1250


def test_detect_ad_intervals_cuts_sponsor_bumper_when_present(tmp_path, monkeypatch):
    """Kui saate tunnus-introle järgneb sponsori kõll (saade_{id}_sponsor_*.wav), lõigatakse ka see välja; kui mitte, ei lõigata saatejuttu."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "puhas_alguskoll.wav").write_bytes(b"dummy")
    (assets_dir / "saade_209_lopukoll_1.wav").write_bytes(b"dummy")
    (assets_dir / "saade_209_sponsor_1.wav").write_bytes(b"dummy")

    fake_audio = tmp_path / "test.mp3"
    fake_audio.write_bytes(b"audio")

    sr = 1000
    monkeypatch.setattr("kuku.jingles.SAMPLE_RATE", sr)

    rng = np.random.default_rng(77)
    intro_wave = rng.standard_normal(sr * 8).astype(np.float32)
    sponsor_wave = rng.standard_normal(sr * 5).astype(np.float32)
    start_jingle_wave = rng.standard_normal(sr * 3).astype(np.float32)

    # Juhtum 1: sponsor on nii alguses (449+8=457..462) kui ka keskmise pausi lõpus (1242+8=1250..1255)
    audio_with_sponsor = rng.standard_normal(sr * 3600).astype(np.float32) * 0.05
    audio_with_sponsor[449 * sr : 457 * sr] += intro_wave * 5.0
    audio_with_sponsor[457 * sr : 462 * sr] += sponsor_wave * 5.0
    audio_with_sponsor[1114 * sr : 1117 * sr] += start_jingle_wave * 5.0
    audio_with_sponsor[1242 * sr : 1250 * sr] += intro_wave * 5.0
    audio_with_sponsor[1250 * sr : 1255 * sr] += sponsor_wave * 5.0

    # Juhtum 2: sponsor puudub (saade algab kohe peale introt 457s pealt)
    audio_no_sponsor = rng.standard_normal(sr * 3600).astype(np.float32) * 0.05
    audio_no_sponsor[449 * sr : 457 * sr] += intro_wave * 5.0

    current_audio = [audio_with_sponsor]

    def mock_load(path, sr=sr):
        p = Path(path).name
        if p == "saade_209_lopukoll_1.wav":
            return intro_wave
        if p == "saade_209_sponsor_1.wav":
            return sponsor_wave
        if p == "puhas_alguskoll.wav":
            return start_jingle_wave
        return current_audio[0]

    monkeypatch.setattr("kuku.jingles.load_audio", mock_load)

    iv_with = detect_ad_intervals(fake_audio, assets_dir=assets_dir, cut_start=True, show_id=209)
    assert iv_with[0] == (0, 462)
    mid = [iv for iv in iv_with if iv[0] == 1114]
    assert len(mid) == 1
    assert mid[0] == (1114, 1255)

    current_audio[0] = audio_no_sponsor
    iv_without = detect_ad_intervals(fake_audio, assets_dir=assets_dir, cut_start=True, show_id=209)
    assert iv_without[0] == (0, 457)


def test_detect_ad_intervals_rounds_up_fractional_intro_end(tmp_path, monkeypatch):
    """Kui intro lõpeb nt 457.4s peal, ümardatakse üles 458s peale, et intro viimane silp ei jääks sisse."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "puhas_alguskoll.wav").write_bytes(b"dummy")
    (assets_dir / "saade_214_lopukoll_1.wav").write_bytes(b"dummy")

    fake_audio = tmp_path / "test.mp3"
    fake_audio.write_bytes(b"audio")

    sr = 1000
    monkeypatch.setattr("kuku.jingles.SAMPLE_RATE", sr)

    rng = np.random.default_rng(99)
    intro_wave = rng.standard_normal(int(sr * 8.4)).astype(np.float32)
    start_jingle_wave = rng.standard_normal(sr * 3).astype(np.float32)

    full_audio = rng.standard_normal(sr * 3600).astype(np.float32) * 0.05
    # Intro 449.0s .. 457.4s -> peab lõikama 458s pealt (mitte 457s)
    full_audio[449 * sr : 449 * sr + len(intro_wave)] += intro_wave * 5.0

    def mock_load(path, sr=sr):
        p = Path(path).name
        if p == "saade_214_lopukoll_1.wav":
            return intro_wave
        if p == "puhas_alguskoll.wav":
            return start_jingle_wave
        return full_audio

    monkeypatch.setattr("kuku.jingles.load_audio", mock_load)

    intervals = detect_ad_intervals(fake_audio, assets_dir=assets_dir, cut_start=True, show_id=214)
    assert intervals[0] == (0, 458)



