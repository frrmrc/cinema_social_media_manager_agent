import re
from pathlib import Path

from social_media_manager_agent.config import get_settings
from social_media_manager_agent.schemas import Post


def sanitize_filename(title: str) -> str:
    safe = re.sub(r"[^\w\s-]", "", title).strip()
    safe = re.sub(r"\s+", "_", safe)
    return safe or "untitled_post"


def save_post(post: Post, save_folder: Path | None = None) -> Path:
    folder = save_folder or get_settings().save_folder
    folder.mkdir(parents=True, exist_ok=True)

    path = folder / f"{sanitize_filename(post.title)}.json"
    path.write_text(post.model_dump_json(indent=2), encoding="utf-8")
    return path

def save_image(image_bytes: bytes, post: Post, save_folder: Path | None = None) -> Path:
    folder = save_folder or get_settings().images_folder
    folder.mkdir(parents=True, exist_ok=True)

    path = folder / f"{sanitize_filename(post.title)}.png"
    path.write_bytes(image_bytes)
    return path