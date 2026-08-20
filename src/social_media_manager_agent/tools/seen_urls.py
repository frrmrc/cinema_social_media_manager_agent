import json
from datetime import date, timedelta
from pathlib import Path

from social_media_manager_agent.config import get_settings
from social_media_manager_agent.schemas import SeenUrl


def _load_all(path: Path) -> list[SeenUrl]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [SeenUrl(**entry) for entry in data]


def load_recent_seen_urls(days: int, path: Path | None = None) -> set[str]:
    file_path = path or get_settings().seen_urls_path
    cutoff = date.today() - timedelta(days=days)
    return {e.url for e in _load_all(file_path) if date.fromisoformat(e.seen_at) >= cutoff}


def record_seen_urls(urls: list[str], path: Path | None = None) -> None:
    if not urls:
        return

    file_path = path or get_settings().seen_urls_path
    entries = _load_all(file_path)
    already_recorded = {e.url for e in entries}
    today_str = date.today().isoformat()
    entries.extend(
        SeenUrl(url=url, seen_at=today_str)
        for url in dict.fromkeys(urls)
        if url not in already_recorded
    )
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps([e.model_dump() for e in entries], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
