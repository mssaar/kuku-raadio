import json
from pathlib import Path
import pytest
from kuku.recut import recut_episode


class DummyGitHub:
    def __init__(self):
        self.releases = {
            "saade-514": {
                "id": 1,
                "name": "Kahe vahel",
                "assets": [
                    {
                        "id": 100,
                        "name": "1792141202.mp3",
                        "browser_download_url": "https://gh/download/1792141202.mp3",
                        "label": "Kahe vahel (16.10.2026)",
                    }
                ],
            }
        }
        self.deleted_assets = []
        self.uploaded = []

    def find_release(self, tag):
        return self.releases.get(tag)

    def list_assets(self, release):
        return {a["name"]: a for a in release.get("assets", [])}

    def delete_asset(self, asset_id):
        self.deleted_assets.append(asset_id)

    def upload_asset(self, release, path, name, label):
        self.uploaded.append((release["id"], path, name, label))
        return {
            "id": 200,
            "name": name,
            "browser_download_url": f"https://gh/download/{name}",
            "label": label,
        }


def test_recut_episode_downloads_cuts_reuploads_and_updates_library(monkeypatch, tmp_path):
    # Mock download_func and remove_ads
    downloaded = []

    def mock_download(url, dest):
        downloaded.append((url, dest))
        Path(dest).write_bytes(b"dummy_data_160000_bytes" + b"\0" * 160000)

    cuts = []

    def mock_remove_ads(inp, outp, intervals):
        cuts.append((inp, outp, intervals))
        # Write dummy output of 16000 * 2585 bytes (simulating 2585 sec @ 128k)
        Path(outp).write_bytes(b"cut" + b"\0" * (16000 * 2585 - 3))

    gh = DummyGitHub()
    lib_file = tmp_path / "library.json"
    lib_file.write_text(
        json.dumps({
            "shows": [
                {
                    "id": 514,
                    "name": "Kahe vahel",
                    "episodes": [
                        {
                            "id": 1792141202,
                            "title": "Kahe vahel (16.10.2026)",
                            "duration_seconds": 3600,
                            "url": "https://gh/download/1792141202.mp3",
                        }
                    ],
                }
            ]
        }),
        encoding="utf-8",
    )

    new_duration = recut_episode(
        github=gh,
        show_id=514,
        episode_id=1792141202,
        ad_intervals=[(0, 115), (670, 800), (1450, 1500), (2150, 2270)],
        library_path=lib_file,
        download_func=mock_download,
        remove_ads_func=mock_remove_ads,
    )

    assert len(downloaded) == 1
    assert downloaded[0][0] == "https://gh/download/1792141202.mp3"

    assert len(cuts) == 1
    assert cuts[0][2] == [(0, 115), (670, 800), (1450, 1500), (2150, 2270)]

    assert gh.deleted_assets == [100]
    assert len(gh.uploaded) == 1
    assert gh.uploaded[0][2] == "1792141202.mp3"
    assert gh.uploaded[0][3] == "Kahe vahel (16.10.2026)"

    # Verify library updated
    saved_lib = json.loads(lib_file.read_text(encoding="utf-8"))
    ep = saved_lib["shows"][0]["episodes"][0]
    assert ep["duration_seconds"] == 2585
    assert new_duration == 2585


def test_recut_episode_prefers_raw_asset_if_available(tmp_path):
    downloaded = []

    def mock_download(url, dest):
        downloaded.append((url, dest))
        Path(dest).write_bytes(b"dummy_data_160000_bytes" + b"\0" * 160000)

    cuts = []

    def mock_remove_ads(inp, outp, intervals):
        cuts.append((inp, outp, intervals))
        Path(outp).write_bytes(b"cut" + b"\0" * (16000 * 2500 - 3))

    gh = DummyGitHub()
    # Add raw asset to dummy release
    gh.releases["saade-514"]["assets"].append({
        "id": 101,
        "name": "raw-1792141202.mp3",
        "browser_download_url": "https://gh/download/raw-1792141202.mp3",
        "label": "Kahe vahel (16.10.2026) (Toorsalvestus)",
    })

    lib_file = tmp_path / "library.json"
    lib_file.write_text(
        json.dumps({
            "shows": [
                {
                    "id": 514,
                    "name": "Kahe vahel",
                    "episodes": [
                        {
                            "id": 1792141202,
                            "title": "Kahe vahel (16.10.2026)",
                            "duration_seconds": 2635,
                            "url": "https://gh/download/1792141202.mp3",
                        }
                    ],
                }
            ]
        }),
        encoding="utf-8",
    )

    new_duration = recut_episode(
        github=gh,
        show_id=514,
        episode_id=1792141202,
        ad_intervals=[(0, 100)],
        library_path=lib_file,
        download_func=mock_download,
        remove_ads_func=mock_remove_ads,
    )

    # Should have downloaded the RAW asset
    assert len(downloaded) == 1
    assert downloaded[0][0] == "https://gh/download/raw-1792141202.mp3"

    # Should have deleted the clean asset (id 100), NOT raw asset (id 101)
    assert gh.deleted_assets == [100]

    # Should upload the new clean asset
    assert gh.uploaded[0][2] == "1792141202.mp3"
    assert new_duration == 2500
