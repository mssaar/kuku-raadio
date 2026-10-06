import pytest
from datetime import datetime, timezone
import pytz

from kuku.live import get_ad_intervals, should_record_now, Schedule

def test_get_ad_intervals_auto():
    # 'auto' should return typical Kuku ad blocks in seconds: 0-5 mins and 30-35 mins
    intervals = get_ad_intervals("auto")
    assert intervals == [(0, 300), (1800, 2100)]

def test_get_ad_intervals_custom():
    intervals = get_ad_intervals("10-15,45-50")
    assert intervals == [(600, 900), (2700, 3000)]

def test_get_ad_intervals_empty():
    assert get_ad_intervals("") == []

def test_should_record_now_matches():
    tz = pytz.timezone("Europe/Tallinn")
    # Wednesday 13:00 (Buum)
    dt = tz.localize(datetime(2026, 10, 7, 13, 5, 0)) # Wednesday
    
    schedule = Schedule(show_id=204, name="Buum", weekday=2, hour=13, duration_minutes=60)
    assert should_record_now(schedule, dt) is True

def test_should_record_now_wrong_hour():
    tz = pytz.timezone("Europe/Tallinn")
    dt = tz.localize(datetime(2026, 10, 7, 14, 5, 0))
    schedule = Schedule(show_id=204, name="Buum", weekday=2, hour=13, duration_minutes=60)
    assert should_record_now(schedule, dt) is False

def test_should_record_now_wrong_day():
    tz = pytz.timezone("Europe/Tallinn")
    dt = tz.localize(datetime(2026, 10, 8, 13, 5, 0)) # Thursday
    schedule = Schedule(show_id=204, name="Buum", weekday=2, hour=13, duration_minutes=60)
    assert should_record_now(schedule, dt) is False

def test_remove_ads(tmp_path, monkeypatch):
    import subprocess
    from kuku.live import remove_ads
    
    # Mock subprocess.run
    called_args = []
    def mock_run(args, **kwargs):
        called_args.append(args)
    
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    input_path = tmp_path / "input.mp3"
    output_path = tmp_path / "output.mp3"
    input_path.write_text("dummy mp3")
    
    # Ads at 10-20 and 40-50
    remove_ads(str(input_path), str(output_path), [(10, 20), (40, 50)])
    
    # Should create segments: 0-10, 20-40, 50-999999
    # That means 3 extract calls, 1 concat call
    assert len(called_args) == 4
    
    # Verify the start/end times in ffmpeg calls
    assert called_args[0][5] == "0"
    assert called_args[0][7] == "10"
    
    assert called_args[1][5] == "20"
    assert called_args[1][7] == "40"
    
    assert called_args[2][5] == "50"
    assert called_args[2][7] == "999999"
    
    # Verify the concat call
    assert called_args[3][0] == "ffmpeg"
    assert "-f" in called_args[3]
    assert "concat" in called_args[3]

