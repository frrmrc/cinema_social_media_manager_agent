from unittest.mock import patch

from social_media_manager_agent.nodes.review_posts import review_posts
from social_media_manager_agent.schemas import Post, PostReview, PostReviews


class _FakeStructuredLLM:
    def __init__(self, result):
        self._result = result

    def invoke(self, prompt):
        return self._result


class _FakeLLM:
    def __init__(self, result):
        self._result = result

    def with_structured_output(self, schema):
        return _FakeStructuredLLM(self._result)


def test_review_posts_applies_decisions_by_position():
    post_a = Post(title="A", body="body a", style="Informative")
    post_b = Post(title="B", body="body b", style="Teaser")

    fake_reviews = PostReviews(
        reviews=[
            PostReview(title="A", approved=True, scheduled_at="2026-08-18T10:00:00", reason="looks good"),
            PostReview(title="B", approved=False, scheduled_at=None, reason="placeholder text"),
        ]
    )

    with patch(
        "social_media_manager_agent.nodes.review_posts.get_llm",
        return_value=_FakeLLM(fake_reviews),
    ), patch("social_media_manager_agent.nodes.review_posts.save_post") as mock_save_post:
        result = review_posts({"posts": [post_a, post_b]})

    assert result == {}
    assert post_a.approved is True
    assert post_a.scheduled_at == "2026-08-18T10:00:00"
    assert post_a.rejection_reason is None
    assert post_b.approved is False
    assert post_b.scheduled_at is None
    assert post_b.rejection_reason == "placeholder text"
    assert mock_save_post.call_count == 2


def test_review_posts_leaves_unapproved_on_count_mismatch():
    post_a = Post(title="A", body="body a", style="Informative")

    fake_reviews = PostReviews(reviews=[])

    with patch(
        "social_media_manager_agent.nodes.review_posts.get_llm",
        return_value=_FakeLLM(fake_reviews),
    ), patch("social_media_manager_agent.nodes.review_posts.save_post") as mock_save_post:
        result = review_posts({"posts": [post_a]})

    assert result == {}
    assert post_a.approved is None
    mock_save_post.assert_not_called()


def test_review_posts_returns_empty_dict_when_no_posts():
    result = review_posts({"posts": []})
    assert result == {}
