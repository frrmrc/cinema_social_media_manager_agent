from unittest.mock import patch

from social_media_manager_agent.nodes.review_posts import review_posts
from social_media_manager_agent.schemas import Post, PostReview, PostReviews


class _FakeStructuredLLM:
    def __init__(self, result, captured_prompts=None):
        self._result = result
        self._captured_prompts = captured_prompts

    def invoke(self, prompt):
        if self._captured_prompts is not None:
            self._captured_prompts.append(prompt)
        return self._result


class _FakeLLM:
    def __init__(self, result, captured_prompts=None):
        self._result = result
        self._captured_prompts = captured_prompts

    def with_structured_output(self, schema):
        return _FakeStructuredLLM(self._result, self._captured_prompts)


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


def test_review_posts_increments_counts_for_approved_movie_posts_only():
    post_a = Post(title="A", body="body a", style="Informative", related_movie_title="Movie A")
    post_b = Post(title="B", body="body b", style="Teaser", related_movie_title="Movie B")

    fake_reviews = PostReviews(
        reviews=[
            PostReview(title="A", approved=True, scheduled_at="2026-08-18T10:00:00", reason="looks good"),
            PostReview(title="B", approved=False, scheduled_at=None, reason="placeholder text"),
        ]
    )

    with patch(
        "social_media_manager_agent.nodes.review_posts.get_llm",
        return_value=_FakeLLM(fake_reviews),
    ), patch("social_media_manager_agent.nodes.review_posts.save_post"), patch(
        "social_media_manager_agent.nodes.review_posts.increment_post_counts"
    ) as mock_increment:
        review_posts({"posts": [post_a, post_b]})

    mock_increment.assert_called_once_with({"Movie A": 1})


def test_review_posts_does_not_increment_on_count_mismatch():
    post_a = Post(title="A", body="body a", style="Informative", related_movie_title="Movie A")

    fake_reviews = PostReviews(reviews=[])

    with patch(
        "social_media_manager_agent.nodes.review_posts.get_llm",
        return_value=_FakeLLM(fake_reviews),
    ), patch("social_media_manager_agent.nodes.review_posts.save_post"), patch(
        "social_media_manager_agent.nodes.review_posts.increment_post_counts"
    ) as mock_increment:
        review_posts({"posts": [post_a]})

    mock_increment.assert_not_called()


def test_review_posts_does_not_increment_when_review_raises():
    post_a = Post(title="A", body="body a", style="Informative", related_movie_title="Movie A")

    class _RaisingLLM:
        def with_structured_output(self, schema):
            raise RuntimeError("boom")

    with patch(
        "social_media_manager_agent.nodes.review_posts.get_llm",
        return_value=_RaisingLLM(),
    ), patch("social_media_manager_agent.nodes.review_posts.increment_post_counts") as mock_increment:
        result = review_posts({"posts": [post_a]})

    assert result == {}
    mock_increment.assert_not_called()


def test_review_posts_uses_movie_release_mode_note_for_movie_release_mode():
    post_a = Post(title="A", body="body a", style="Informative", related_movie_title="Movie A")
    fake_reviews = PostReviews(
        reviews=[PostReview(title="A", approved=True, scheduled_at="2026-08-18T10:00:00", reason="ok")]
    )
    captured = []

    with patch(
        "social_media_manager_agent.nodes.review_posts.get_llm",
        return_value=_FakeLLM(fake_reviews, captured),
    ), patch("social_media_manager_agent.nodes.review_posts.save_post"), patch(
        "social_media_manager_agent.nodes.review_posts.increment_post_counts"
    ):
        review_posts({"posts": [post_a], "mode": "movie_release"})

    assert len(captured) == 1
    assert "Do NOT reject a post solely for stating a movie's release or screening date" in captured[0]


def test_review_posts_uses_generic_news_mode_note_for_generic_news_mode():
    post_a = Post(title="A", body="body a", style="Informative")
    fake_reviews = PostReviews(
        reviews=[PostReview(title="A", approved=True, scheduled_at="2026-08-18T10:00:00", reason="ok")]
    )
    captured = []

    with patch(
        "social_media_manager_agent.nodes.review_posts.get_llm",
        return_value=_FakeLLM(fake_reviews, captured),
    ), patch("social_media_manager_agent.nodes.review_posts.save_post"), patch(
        "social_media_manager_agent.nodes.review_posts.increment_post_counts"
    ):
        review_posts({"posts": [post_a], "mode": "generic_news"})

    assert len(captured) == 1
    assert "Treat any specific movie release/screening date mentioned as an unverifiable claim" in captured[0]


def test_review_posts_defaults_to_generic_news_mode_note_when_mode_missing():
    post_a = Post(title="A", body="body a", style="Informative")
    fake_reviews = PostReviews(
        reviews=[PostReview(title="A", approved=True, scheduled_at="2026-08-18T10:00:00", reason="ok")]
    )
    captured = []

    with patch(
        "social_media_manager_agent.nodes.review_posts.get_llm",
        return_value=_FakeLLM(fake_reviews, captured),
    ), patch("social_media_manager_agent.nodes.review_posts.save_post"), patch(
        "social_media_manager_agent.nodes.review_posts.increment_post_counts"
    ):
        review_posts({"posts": [post_a]})

    assert len(captured) == 1
    assert "Treat any specific movie release/screening date mentioned as an unverifiable claim" in captured[0]
