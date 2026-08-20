import json
from datetime import date, timedelta

from social_media_manager_agent.tools.seen_urls import load_recent_seen_urls, record_seen_urls


def test_load_recent_seen_urls_filters_old_entries(tmp_path):
    seen_file = tmp_path / "seen_urls.json"
    recent = date.today().isoformat()
    old = (date.today() - timedelta(days=90)).isoformat()
    seen_file.write_text(
        json.dumps([
            {"url": "https://recent.example/a", "seen_at": recent},
            {"url": "https://old.example/b", "seen_at": old},
        ]),
        encoding="utf-8",
    )

    result = load_recent_seen_urls(days=45, path=seen_file)

    assert result == {"https://recent.example/a"}


def test_load_recent_seen_urls_empty_when_no_file(tmp_path):
    seen_file = tmp_path / "seen_urls.json"

    assert load_recent_seen_urls(days=45, path=seen_file) == set()


def test_record_seen_urls_appends_new_entries(tmp_path):
    seen_file = tmp_path / "seen_urls.json"

    record_seen_urls(["https://a.example", "https://b.example"], path=seen_file)

    data = json.loads(seen_file.read_text(encoding="utf-8"))
    assert {e["url"] for e in data} == {"https://a.example", "https://b.example"}
    assert all(e["seen_at"] == date.today().isoformat() for e in data)


def test_record_seen_urls_does_not_duplicate_existing_urls(tmp_path):
    seen_file = tmp_path / "seen_urls.json"
    old = (date.today() - timedelta(days=10)).isoformat()
    seen_file.write_text(
        json.dumps([{"url": "https://a.example", "seen_at": old}]),
        encoding="utf-8",
    )

    record_seen_urls(["https://a.example", "https://c.example"], path=seen_file)

    data = json.loads(seen_file.read_text(encoding="utf-8"))
    assert len(data) == 2
    a_entry = next(e for e in data if e["url"] == "https://a.example")
    assert a_entry["seen_at"] == old


def test_record_seen_urls_noop_on_empty_list(tmp_path):
    seen_file = tmp_path / "seen_urls.json"

    record_seen_urls([], path=seen_file)

    assert not seen_file.exists()
