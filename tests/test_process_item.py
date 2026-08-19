from unittest.mock import patch

from social_media_manager_agent.nodes.process_item import _find_movie, write_post
from social_media_manager_agent.schemas import DraftPost, MovieRelease, SelectedItem


class _FakeStructuredLLM:
    def __init__(self, result, captured_prompts=None):
        self._result = result
        self.received_schema = None
        self._captured_prompts = captured_prompts

    def invoke(self, prompt):
        if self._captured_prompts is not None:
            self._captured_prompts.append(prompt)
        return self._result


class _FakeLLM:
    def __init__(self, result, captured_prompts=None):
        self._result = result
        self.requested_schema = None
        self._captured_prompts = captured_prompts

    def with_structured_output(self, schema):
        self.requested_schema = schema
        return _FakeStructuredLLM(self._result, self._captured_prompts)


def test_write_post_requests_draft_post_schema_without_publish_at():
    fake_draft = DraftPost(title="Title", body="Body", style="Informative")
    fake_llm = _FakeLLM(fake_draft)

    item = SelectedItem(title="Idea", summary="Summary", reason="Relevant")

    with patch("social_media_manager_agent.nodes.process_item.get_llm", return_value=fake_llm):
        post = write_post(item, briefing="- fact one")

    assert fake_llm.requested_schema is DraftPost
    assert post.title == "Title"
    assert post.body == "Body"
    assert post.style == "Informative"
    assert not hasattr(post, "publish_at")
    assert post.approved is None
    assert post.scheduled_at is None
    assert post.published is False


def test_write_post_movie_release_mode_includes_title_and_release_date():
    fake_draft = DraftPost(title="Title", body="Body", style="Informative")
    captured = []
    fake_llm = _FakeLLM(fake_draft, captured)

    item = SelectedItem(title="Idea", summary="Summary", reason="Relevant", related_movie_title="Movie A")
    movie = MovieRelease(title="Movie A", release_date="2026-09-10")

    with patch("social_media_manager_agent.nodes.process_item.get_llm", return_value=fake_llm):
        write_post(item, briefing="- fact one", mode="movie_release", movie=movie)

    assert len(captured) == 1
    prompt = captured[0]
    assert "make people want to come watch it at" in prompt
    assert 'movie "Movie A"' in prompt
    assert "2026-09-10" in prompt


def test_write_post_movie_release_mode_falls_back_without_movie_lookup():
    fake_draft = DraftPost(title="Title", body="Body", style="Informative")
    captured = []
    fake_llm = _FakeLLM(fake_draft, captured)

    item = SelectedItem(title="Idea", summary="Summary", reason="Relevant", related_movie_title="Movie A")

    with patch("social_media_manager_agent.nodes.process_item.get_llm", return_value=fake_llm):
        write_post(item, briefing="- fact one", mode="movie_release")

    assert len(captured) == 1
    assert 'movie "Movie A"' in captured[0]


def test_write_post_uses_generic_news_mode_note_for_generic_news_mode():
    fake_draft = DraftPost(title="Title", body="Body", style="Informative")
    captured = []
    fake_llm = _FakeLLM(fake_draft, captured)

    item = SelectedItem(title="Idea", summary="Summary", reason="Relevant")

    with patch("social_media_manager_agent.nodes.process_item.get_llm", return_value=fake_llm):
        write_post(item, briefing="- fact one", mode="generic_news")

    assert len(captured) == 1
    assert "not to promote a specific screening" in captured[0]


def test_find_movie_matches_by_title():
    movies = [MovieRelease(title="Movie A", release_date="2026-09-10"), MovieRelease(title="Movie B", release_date="2026-09-11")]

    assert _find_movie("Movie B", movies).release_date == "2026-09-11"
    assert _find_movie("Missing", movies) is None
    assert _find_movie(None, movies) is None


def test_write_post_defaults_to_generic_news_mode_note_when_mode_missing():
    fake_draft = DraftPost(title="Title", body="Body", style="Informative")
    captured = []
    fake_llm = _FakeLLM(fake_draft, captured)

    item = SelectedItem(title="Idea", summary="Summary", reason="Relevant")

    with patch("social_media_manager_agent.nodes.process_item.get_llm", return_value=fake_llm):
        write_post(item, briefing="- fact one")

    assert len(captured) == 1
    assert "not to promote a specific screening" in captured[0]
