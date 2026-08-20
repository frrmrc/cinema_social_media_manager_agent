from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

from social_media_manager_agent.schemas import Post
from social_media_manager_agent.tools.cloudinary import CloudinaryUpload
from social_media_manager_agent.tools.publisher import publish_due_posts
from social_media_manager_agent.tools.storage import save_image, save_post

LOCAL_TZ = ZoneInfo("Europe/Rome")


def _local_now():
    """Naive local time, as the reviewer would write into scheduled_at."""
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ).replace(tzinfo=None)


def _make_post(tmp_path, **overrides):
    defaults = dict(title="Default Title", body="body", style="Informative")
    defaults.update(overrides)
    return Post(**defaults)


def test_publish_due_posts_publishes_only_due_approved_posts(tmp_path):
    due_post = _make_post(
        tmp_path,
        title="Due Post",
        approved=True,
        scheduled_at=(_local_now() - timedelta(minutes=5)).isoformat(),
    )
    image_path = save_image(b"fake-bytes", due_post, save_folder=tmp_path)
    due_post.image_path = str(image_path)
    save_post(due_post, save_folder=tmp_path)

    not_due_post = _make_post(
        tmp_path,
        title="Not Due Post",
        approved=True,
        scheduled_at=(_local_now() + timedelta(hours=1)).isoformat(),
    )
    save_post(not_due_post, save_folder=tmp_path)

    unapproved_post = _make_post(tmp_path, title="Unapproved Post")
    save_post(unapproved_post, save_folder=tmp_path)

    already_published_post = _make_post(
        tmp_path,
        title="Already Published Post",
        approved=True,
        scheduled_at=(_local_now() - timedelta(minutes=5)).isoformat(),
        published=True,
    )
    save_post(already_published_post, save_folder=tmp_path)

    with patch(
        "social_media_manager_agent.tools.publisher.upload_image_to_cloudinary",
        return_value=CloudinaryUpload(url="https://res.cloudinary.com/demo/image/upload/abc/img.png", public_id="abc/img"),
    ) as mock_upload, patch(
        "social_media_manager_agent.tools.publisher.wait_until_publicly_reachable"
    ) as mock_verify, patch(
        "social_media_manager_agent.tools.publisher.publish_image_post", return_value="media-123"
    ) as mock_publish, patch(
        "social_media_manager_agent.tools.publisher.delete_image_from_cloudinary"
    ) as mock_delete:
        published, skipped = publish_due_posts(posts_folder=tmp_path)

    assert published == ["Due Post"]
    assert set(skipped) == {"Not Due Post", "Unapproved Post", "Already Published Post"}
    mock_upload.assert_called_once()
    mock_verify.assert_called_once_with("https://res.cloudinary.com/demo/image/upload/abc/img.png")
    mock_publish.assert_called_once_with("https://res.cloudinary.com/demo/image/upload/abc/img.png", "body")
    mock_delete.assert_called_once_with("abc/img")

    updated = Post.model_validate_json((tmp_path / "Due_Post.json").read_text(encoding="utf-8"))
    assert updated.published is True
    assert updated.instagram_media_id == "media-123"
    assert updated.cloudinary_public_id is None


def test_publish_due_posts_leaves_post_unpublished_if_graph_api_fails(tmp_path):
    due_post = _make_post(
        tmp_path,
        title="Failing Post",
        approved=True,
        scheduled_at=(_local_now() - timedelta(minutes=5)).isoformat(),
    )
    image_path = save_image(b"fake-bytes", due_post, save_folder=tmp_path)
    due_post.image_path = str(image_path)
    save_post(due_post, save_folder=tmp_path)

    with patch(
        "social_media_manager_agent.tools.publisher.upload_image_to_cloudinary",
        return_value=CloudinaryUpload(url="https://res.cloudinary.com/demo/image/upload/abc/img.png", public_id="abc/img"),
    ), patch(
        "social_media_manager_agent.tools.publisher.wait_until_publicly_reachable"
    ), patch(
        "social_media_manager_agent.tools.publisher.publish_image_post",
        side_effect=RuntimeError("graph api down"),
    ), patch(
        "social_media_manager_agent.tools.publisher.delete_image_from_cloudinary"
    ) as mock_delete:
        published, skipped = publish_due_posts(posts_folder=tmp_path)

    assert published == []
    assert skipped == ["Failing Post"]
    mock_delete.assert_called_once_with("abc/img")

    updated = Post.model_validate_json((tmp_path / "Failing_Post.json").read_text(encoding="utf-8"))
    assert updated.published is False
    assert updated.cloudinary_public_id is None


def test_publish_due_posts_skips_post_when_verification_fails(tmp_path):
    due_post = _make_post(
        tmp_path,
        title="Unreachable Post",
        approved=True,
        scheduled_at=(_local_now() - timedelta(minutes=5)).isoformat(),
    )
    image_path = save_image(b"fake-bytes", due_post, save_folder=tmp_path)
    due_post.image_path = str(image_path)
    save_post(due_post, save_folder=tmp_path)

    with patch(
        "social_media_manager_agent.tools.publisher.upload_image_to_cloudinary",
        return_value=CloudinaryUpload(url="https://res.cloudinary.com/demo/image/upload/abc/img.png", public_id="abc/img"),
    ), patch(
        "social_media_manager_agent.tools.publisher.wait_until_publicly_reachable",
        side_effect=RuntimeError("not reachable"),
    ), patch(
        "social_media_manager_agent.tools.publisher.publish_image_post"
    ) as mock_publish, patch(
        "social_media_manager_agent.tools.publisher.delete_image_from_cloudinary"
    ) as mock_delete:
        published, skipped = publish_due_posts(posts_folder=tmp_path)

    assert published == []
    assert skipped == ["Unreachable Post"]
    mock_publish.assert_not_called()
    mock_delete.assert_called_once_with("abc/img")

    updated = Post.model_validate_json((tmp_path / "Unreachable_Post.json").read_text(encoding="utf-8"))
    assert updated.published is False
    assert updated.cloudinary_public_id is None


def test_publish_due_posts_publish_succeeds_even_if_cloudinary_delete_fails(tmp_path):
    due_post = _make_post(
        tmp_path,
        title="Delete Failing Post",
        approved=True,
        scheduled_at=(_local_now() - timedelta(minutes=5)).isoformat(),
    )
    image_path = save_image(b"fake-bytes", due_post, save_folder=tmp_path)
    due_post.image_path = str(image_path)
    save_post(due_post, save_folder=tmp_path)

    with patch(
        "social_media_manager_agent.tools.publisher.upload_image_to_cloudinary",
        return_value=CloudinaryUpload(url="https://res.cloudinary.com/demo/image/upload/abc/img.png", public_id="abc/img"),
    ), patch(
        "social_media_manager_agent.tools.publisher.wait_until_publicly_reachable"
    ), patch(
        "social_media_manager_agent.tools.publisher.publish_image_post", return_value="media-123"
    ), patch(
        "social_media_manager_agent.tools.publisher.delete_image_from_cloudinary",
        side_effect=RuntimeError("cloudinary down"),
    ):
        published, skipped = publish_due_posts(posts_folder=tmp_path)

    assert published == ["Delete Failing Post"]
    assert skipped == []

    updated = Post.model_validate_json((tmp_path / "Delete_Failing_Post.json").read_text(encoding="utf-8"))
    assert updated.published is True
    assert updated.instagram_media_id == "media-123"
    assert updated.cloudinary_public_id == "abc/img"


def test_publish_due_posts_skips_post_without_image(tmp_path):
    due_post = _make_post(
        tmp_path,
        title="No Image Post",
        approved=True,
        scheduled_at=(_local_now() - timedelta(minutes=5)).isoformat(),
    )
    save_post(due_post, save_folder=tmp_path)

    published, skipped = publish_due_posts(posts_folder=tmp_path)

    assert published == []
    assert skipped == ["No Image Post"]
