import logging
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from social_media_manager_agent.config import get_settings
from social_media_manager_agent.schemas import Post
from social_media_manager_agent.tools.cloudinary import (
    delete_image_from_cloudinary,
    upload_image_to_cloudinary,
    wait_until_publicly_reachable,
)
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


def _is_due(post: Post, now: datetime, local_tz: ZoneInfo) -> bool:
    if not post.approved or post.published or not post.scheduled_at:
        return False
    try:
        # scheduled_at is a naive local-time string (the reviewer's timezone), not UTC
        scheduled = datetime.fromisoformat(post.scheduled_at).replace(tzinfo=local_tz)
    except ValueError:
        logger.warning("Invalid scheduled_at for '%s': %s", post.title, post.scheduled_at)
        return False
    return scheduled <= now


def _cleanup_cloudinary_asset(post: Post, public_id: str, folder: Path) -> None:
    try:
        delete_image_from_cloudinary(public_id)
        post.cloudinary_public_id = None
        save_post(post, save_folder=folder)
    except Exception:
        logger.warning("Failed to delete Cloudinary asset %s for '%s'", public_id, post.title, exc_info=True)


def publish_due_posts(posts_folder: Path | None = None) -> tuple[list[str], list[str]]:
    settings = get_settings()
    folder = posts_folder or settings.save_folder
    now = datetime.now(timezone.utc)
    local_tz = ZoneInfo(settings.timezone)

    published: list[str] = []
    skipped: list[str] = []

    for post in _load_posts(folder):
        if not _is_due(post, now, local_tz):
            skipped.append(post.title)
            continue

        if not post.image_path or not Path(post.image_path).exists():
            logger.warning("No image available for '%s', cannot publish", post.title)
            skipped.append(post.title)
            continue

        public_id: str | None = None
        try:
            image_url, public_id = upload_image_to_cloudinary(Path(post.image_path))
            post.cloudinary_public_id = public_id
            save_post(post, save_folder=folder)

            wait_until_publicly_reachable(image_url)
            media_id = publish_image_post(image_url, post.body)

            post.published = True
            post.instagram_media_id = media_id
            save_post(post, save_folder=folder)
            published.append(post.title)
            logger.info("Published '%s' to Instagram (media_id=%s)", post.title, media_id)
            _cleanup_cloudinary_asset(post, public_id, folder)
        except Exception:
            logger.warning("Failed to publish '%s'", post.title, exc_info=True)
            skipped.append(post.title)
            if public_id is not None:
                _cleanup_cloudinary_asset(post, public_id, folder)

    return published, skipped
