import json
from datetime import date, timedelta

from social_media_manager_agent.tools.history import load_recent_history


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