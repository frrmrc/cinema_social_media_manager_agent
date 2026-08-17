from datetime import datetime, timedelta
from unittest.mock import patch

from social_media_manager_agent.schemas import Post
from social_media_manager_agent.tools.publisher import publish_due_posts
from social_media_manager_agent.tools.storage import save_image, save_post


def _make_post(tmp_path, **overrides):
    defaults = dict(title="Default Title", body="body", style="Informative")
    defaults.update(overrides)
    return Post(**defaults)


def test_publish_due_posts_publishes_only_due_approved_posts(tmp_path):
    due_post = _make_post(
        tmp_path,
        title="Due Post",
        approved=True,
        scheduled_at=(datetime.now() - timedelta(minutes=5)).isoformat(),
    )
    image_path = save_image(b"fake-bytes", due_post, save_folder=tmp_path)
    due_post.image_path = str(image_path)
    save_post(due_post, save_folder=tmp_path)

    not_due_post = _make_post(
        tmp_path,
        title="Not Due Post",
        approved=True,
        scheduled_at=(datetime.now() + timedelta(hours=1)).isoformat(),
    )
    save_post(not_due_post, save_folder=tmp_path)

    unapproved_post = _make_post(tmp_path, title="Unapproved Post")
    save_post(unapproved_post, save_folder=tmp_path)

    already_published_post = _make_post(
        tmp_path,
        title="Already Published Post",
        approved=True,
        scheduled_at=(datetime.now() - timedelta(minutes=5)).isoformat(),
        published=True,
    )
    save_post(already_published_post, save_folder=tmp_path)

    with patch(
        "social_media_manager_agent.tools.publisher.upload_image_to_imgbb",
        return_value="https://i.ibb.co/abc/img.png",
    ) as mock_upload, patch(
        "social_media_manager_agent.tools.publisher.publish_image_post", return_value="media-123"
    ) as mock_publish:
        published, skipped = publish_due_posts(posts_folder=tmp_path)

    assert published == ["Due Post"]
    assert set(skipped) == {"Not Due Post", "Unapproved Post", "Already Published Post"}
    mock_upload.assert_called_once()
    mock_publish.assert_called_once_with("https://i.ibb.co/abc/img.png", "body")

    updated = Post.model_validate_json((tmp_path / "Due_Post.json").read_text(encoding="utf-8"))
    assert updated.published is True
    assert updated.instagram_media_id == "media-123"


def test_publish_due_posts_leaves_post_unpublished_if_graph_api_fails(tmp_path):
    due_post = _make_post(
        tmp_path,
        title="Failing Post",
        approved=True,
        scheduled_at=(datetime.now() - timedelta(minutes=5)).isoformat(),
    )
    image_path = save_image(b"fake-bytes", due_post, save_folder=tmp_path)
    due_post.image_path = str(image_path)
    save_post(due_post, save_folder=tmp_path)

    with patch(
        "social_media_manager_agent.tools.publisher.upload_image_to_imgbb",
        return_value="https://i.ibb.co/abc/img.png",
    ), patch(
        "social_media_manager_agent.tools.publisher.publish_image_post",
        side_effect=RuntimeError("graph api down"),
    ):
        published, skipped = publish_due_posts(posts_folder=tmp_path)

    assert published == []
    assert skipped == ["Failing Post"]

    updated = Post.model_validate_json((tmp_path / "Failing_Post.json").read_text(encoding="utf-8"))
    assert updated.published is False


def test_publish_due_posts_skips_post_without_image(tmp_path):
    due_post = _make_post(
        tmp_path,
        title="No Image Post",
        approved=True,
        scheduled_at=(datetime.now() - timedelta(minutes=5)).isoformat(),
    )
    save_post(due_post, save_folder=tmp_path)

    published, skipped = publish_due_posts(posts_folder=tmp_path)

    assert published == []
    assert skipped == ["No Image Post"]
