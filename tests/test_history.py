import json
from datetime import date, timedelta

from social_media_manager_agent.tools.history import load_recent_history, titles_posted_today


def test_load_recent_history_filters_old_entries(tmp_path):
    history_file = tmp_path / "history.json"
    recent = date.today().isoformat()
    old = (date.today() - timedelta(days=30)).isoformat()
    history_file.write_text(
        json.dumps([
            {"title": "Recent", "summary": "...", "related_movie_title": None, "created_at": recent},
            {"title": "Old", "summary": "...", "related_movie_title": None, "created_at": old},
        ]),
        encoding="utf-8",
    )

    entries = load_recent_history(days=15, history_path=history_file)

    assert len(entries) == 1
    assert entries[0].title == "Recent"


def test_titles_posted_today_returns_only_todays_movie_titles(tmp_path):
    history_file = tmp_path / "history.json"
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    history_file.write_text(
        json.dumps([
            {"title": "A", "summary": "...", "related_movie_title": "Movie A", "created_at": today},
            {"title": "B", "summary": "...", "related_movie_title": "Movie B", "created_at": yesterday},
            {"title": "C", "summary": "...", "related_movie_title": None, "created_at": today},
        ]),
        encoding="utf-8",
    )

    result = titles_posted_today(history_path=history_file)

    assert result == {"Movie A"}


def test_titles_posted_today_empty_when_no_history(tmp_path):
    history_file = tmp_path / "history.json"

    assert titles_posted_today(history_path=history_file) == set()