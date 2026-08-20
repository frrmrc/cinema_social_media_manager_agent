from unittest.mock import MagicMock, patch

from social_media_manager_agent.tools.search import broad_search, focused_search


def _mock_settings():
    settings = MagicMock()
    settings.tavily_api_key = "test-key"
    return settings


def test_broad_search_uses_news_topic_and_time_range():
    with patch("social_media_manager_agent.tools.search.get_settings", return_value=_mock_settings()), patch(
        "social_media_manager_agent.tools.search.TavilySearch"
    ) as mock_cls:
        mock_cls.return_value.invoke.return_value = {"results": []}

        broad_search("some query", max_results=5, time_range="week")

    _, kwargs = mock_cls.call_args
    assert kwargs["topic"] == "news"
    assert kwargs["time_range"] == "week"
    assert kwargs["max_results"] == 5


def test_focused_search_uses_general_topic():
    with patch("social_media_manager_agent.tools.search.get_settings", return_value=_mock_settings()), patch(
        "social_media_manager_agent.tools.search.TavilySearch"
    ) as mock_cls:
        mock_cls.return_value.invoke.return_value = {"results": []}

        focused_search("some query", max_results=4)

    _, kwargs = mock_cls.call_args
    assert kwargs["topic"] == "general"
    assert kwargs["time_range"] is None
