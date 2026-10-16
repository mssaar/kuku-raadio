import pytest
from datetime import datetime, timezone
import pytz

from kuku.live import get_ad_intervals, should_record_now, compute_recording_plan, Schedule

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

def test_should_record_now_before_hour_and_midnight():
    tz = pytz.timezone("Europe/Tallinn")
    # Woken up at 12:52 on Wednesday for 13:00 show
    dt_pre = tz.localize(datetime(2026, 10, 7, 12, 52, 0))
    schedule = Schedule(show_id=204, name="Buum", weekday=2, hour=13, duration_minutes=60)
    assert should_record_now(schedule, dt_pre) is True

    # Woken up at 23:52 on Tuesday for Wednesday 00:00 show
    dt_midnight = tz.localize(datetime(2026, 10, 6, 23, 52, 0)) # Tuesday 23:52
    schedule_midnight = Schedule(show_id=999, name="Öösaade", weekday=2, hour=0, duration_minutes=60)
    assert should_record_now(schedule_midnight, dt_midnight) is True

def test_compute_recording_plan_waits_for_top_of_hour():
    tz = pytz.timezone("Europe/Tallinn")
    # Woken up at 12:52:10 for 13:00 show -> wait 7 min 50 sec (470s), record full 60 min
    dt = tz.localize(datetime(2026, 10, 7, 12, 52, 10))
    schedule = Schedule(show_id=204, name="Buum", weekday=2, hour=13, duration_minutes=60)
    wait_sec, duration_min = compute_recording_plan(schedule, dt)
    assert wait_sec == 470
    assert duration_min == 60

def test_compute_recording_plan_late_wakeup_trims_duration():
    tz = pytz.timezone("Europe/Tallinn")
    # Woken up late at 13:04:20 for 13:00 show -> wait 0s, record remaining 56 min
    dt = tz.localize(datetime(2026, 10, 7, 13, 4, 20))
    schedule = Schedule(show_id=204, name="Buum", weekday=2, hour=13, duration_minutes=60)
    wait_sec, duration_min = compute_recording_plan(schedule, dt)
    assert wait_sec == 0
    assert duration_min == 56

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


def test_auto_record_waits_until_hour_before_recording(monkeypatch, tmp_path):
    import json
    import subprocess
    import kuku.auto_record as auto_record
    from kuku.api import Episode

    shows_file = tmp_path / "shows.json"
    shows_file.write_text(json.dumps([{"id": 214, "name": "Buum"}]), encoding="utf-8")
    monkeypatch.setattr(auto_record, "DATA_DIR", tmp_path)

    tz = pytz.timezone("Europe/Tallinn")
    fake_now = tz.localize(datetime(2026, 10, 7, 12, 52, 15))  # Wed 12:52:15 -> 465s before 13:00

    slept = []
    monkeypatch.setattr(auto_record.time, "sleep", lambda s: slept.append(s))

    ep = Episode(
        id=1,
        title="Buum",
        published_at=tz.localize(datetime(2026, 9, 30, 13, 0)).astimezone(timezone.utc),
        is_premium=False,
        is_playable=True,
        duration_seconds=3600,
    )
    monkeypatch.setattr(auto_record.KukuClient, "list_episodes", lambda self, sid, since: [ep])

    cmds = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: cmds.append(cmd))

    auto_record.main(now_override=fake_now)

    assert slept == [465]
    assert len(cmds) == 1
    assert "--duration" in cmds[0]
    assert cmds[0][cmds[0].index("--duration") + 1] == "60"


def test_auto_record_10min_test_mode(monkeypatch, tmp_path):
    import json
    import subprocess
    import kuku.auto_record as auto_record

    shows_file = tmp_path / "shows.json"
    shows_file.write_text(json.dumps([{"id": 209, "name": "Digitund"}]), encoding="utf-8")
    monkeypatch.setattr(auto_record, "DATA_DIR", tmp_path)
    monkeypatch.setenv("TEST_RECORD_MINUTES", "10")
    monkeypatch.setenv("TEST_START_TIME", "09:30")

    tz = pytz.timezone("Europe/Tallinn")
    fake_now = tz.localize(datetime(2026, 10, 16, 9, 28, 40))  # 80s before 09:30

    slept = []
    monkeypatch.setattr(auto_record.time, "sleep", lambda s: slept.append(s))

    cmds = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: cmds.append(cmd))

    auto_record.main(now_override=fake_now)

    assert slept == [80]
    assert len(cmds) == 1
    assert "--duration" in cmds[0]
    assert cmds[0][cmds[0].index("--duration") + 1] == "10"


