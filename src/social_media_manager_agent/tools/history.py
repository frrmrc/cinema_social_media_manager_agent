import json
from datetime import date, timedelta
from pathlib import Path

from social_media_manager_agent.config import get_settings
from social_media_manager_agent.schemas import HistoryEntry, SelectedItem


def _load_all(history_path: Path) -> list[HistoryEntry]:
    if not history_path.exists():
        return []
    data = json.loads(history_path.read_text(encoding="utf-8"))
    return [HistoryEntry(**entry) for entry in data]


def load_recent_history(days: int = 15, history_path: Path | None = None) -> list[HistoryEntry]:
    path = history_path or get_settings().history_path
    cutoff = date.today() - timedelta(days=days)
    return [e for e in _load_all(path) if date.fromisoformat(e.created_at) >= cutoff]


def append_to_history(items: list[SelectedItem], history_path: Path | None = None) -> None:
    if not items:
        return

    path = history_path or get_settings().history_path
    entries = _load_all(path)
    today_str = date.today().isoformat()
    entries.extend(
        HistoryEntry(
            title=item.title,
            summary=item.summary,
            related_movie_title=item.related_movie_title,
            created_at=today_str,
        )
        for item in items
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([e.model_dump() for e in entries], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def format_history(entries: list[HistoryEntry]) -> str:
    if not entries:
        return "(none)"
    return "\n".join(f"- {e.title}: {e.summary}" for e in entries)