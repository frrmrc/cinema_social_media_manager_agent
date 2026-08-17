import logging
from datetime import datetime
from pathlib import Path

from social_media_manager_agent.config import get_settings
from social_media_manager_agent.schemas import Post
from social_media_manager_agent.tools.imgbb import upload_image_to_imgbb
from social_media_manager_agent.tools.instagram import publish_image_post
from social_media_manager_agent.tools.storage import save_post

logger = logging.getLogger(__name__)


def _load_posts(posts_folder: Path) -> list[Post]:
    posts = []
    for path in posts_folder.glob("*.json"):
        try:
            posts.append(Post.model_validate_json(path.read_text(encoding="utf-8")))
        except Exception:
            logger.warning("Could not parse post file %s", path, exc_info=True)
    return posts


def _is_due(post: Post, now: datetime) -> bool:
    if not post.approved or post.published or not post.scheduled_at:
        return False
    try:
        scheduled = datetime.fromisoformat(post.scheduled_at)
    except ValueError:
        logger.warning("Invalid scheduled_at for '%s': %s", post.title, post.scheduled_at)
        return False
    return scheduled <= now


def publish_due_posts(posts_folder: Path | None = None) -> tuple[list[str], list[str]]:
    folder = posts_folder or get_settings().save_folder
    now = datetime.now()

    published: list[str] = []
    skipped: list[str] = []

    for post in _load_posts(folder):
        if not _is_due(post, now):
            skipped.append(post.title)
            continue

        if not post.image_path or not Path(post.image_path).exists():
            logger.warning("No image available for '%s', cannot publish", post.title)
            skipped.append(post.title)
            continue

        try:
            image_url = upload_image_to_imgbb(Path(post.image_path))
            media_id = publish_image_post(image_url, post.body)

            post.published = True
            post.instagram_media_id = media_id
            save_post(post, save_folder=folder)
            published.append(post.title)
            logger.info("Published '%s' to Instagram (media_id=%s)", post.title, media_id)
        except Exception:
            logger.warning("Failed to publish '%s'", post.title, exc_info=True)
            skipped.append(post.title)

    return published, skipped
