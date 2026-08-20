from unittest.mock import patch

from social_media_manager_agent.nodes.discovery import discover_generic_news, discover_movie_releases
from social_media_manager_agent.schemas import CandidateItems, MovieRelease


class _FakeStructuredLLM:
    def __init__(self, result):
        self._result = result
        self.last_prompt = None

    def invoke(self, prompt):
        self.last_prompt = prompt
        return self._result


class _FakeLLM:
    def __init__(self, result):
        self.structured = _FakeStructuredLLM(result)

    def with_structured_output(self, schema):
        return self.structured


_SEARCH_RESULTS = [
    {"url": "https://old.example/seen", "title": "Old news", "content": "stale content"},
    {"url": "https://new.example/fresh", "title": "Fresh news", "content": "brand new content"},
]


def test_discover_generic_news_filters_seen_urls_and_records_all():
    fake_llm = _FakeLLM(CandidateItems(items=[]))

    with patch(
        "social_media_manager_agent.nodes.discovery.broad_search", return_value=_SEARCH_RESULTS
    ), patch(
        "social_media_manager_agent.nodes.discovery.load_recent_seen_urls",
        return_value={"https://old.example/seen"},
    ), patch(
        "social_media_manager_agent.nodes.discovery.record_seen_urls"
    ) as mock_record, patch(
        "social_media_manager_agent.nodes.discovery.get_llm", return_value=fake_llm
    ):
        discover_generic_news({})

    prompt = fake_llm.structured.last_prompt
    assert "brand new content" in prompt
    assert "stale content" not in prompt
    mock_record.assert_called_once()
    assert set(mock_record.call_args[0][0]) == {"https://old.example/seen", "https://new.example/fresh"}


def test_discover_movie_releases_filters_seen_urls_and_records_all():
    fake_llm = _FakeLLM(CandidateItems(items=[]))
    movie = MovieRelease(title="Movie A", release_date="2026-09-01")

    with patch(
        "social_media_manager_agent.nodes.discovery.load_upcoming_movies", return_value=[movie]
    ), patch(
        "social_media_manager_agent.nodes.discovery.filter_eligible_movies", return_value=[movie]
    ), patch(
        "social_media_manager_agent.nodes.discovery.titles_posted_today", return_value=set()
    ), patch(
        "social_media_manager_agent.nodes.discovery.broad_search", return_value=_SEARCH_RESULTS
    ), patch(
        "social_media_manager_agent.nodes.discovery.load_recent_seen_urls",
        return_value={"https://old.example/seen"},
    ), patch(
        "social_media_manager_agent.nodes.discovery.record_seen_urls"
    ) as mock_record, patch(
        "social_media_manager_agent.nodes.discovery.get_llm", return_value=fake_llm
    ):
        discover_movie_releases({"mode": "movie_release"})

    prompt = fake_llm.structured.last_prompt
    assert "brand new content" in prompt
    assert "stale content" not in prompt
    mock_record.assert_called_once()
    assert set(mock_record.call_args[0][0]) == {"https://old.example/seen", "https://new.example/fresh"}
