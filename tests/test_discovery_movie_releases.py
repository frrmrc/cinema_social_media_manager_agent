from unittest.mock import patch

from social_media_manager_agent.nodes.discovery import discover_movie_releases


def test_discover_movie_releases_short_circuits_when_no_eligible_movies():
    with patch(
        "social_media_manager_agent.nodes.discovery.load_upcoming_movies",
        return_value=[],
    ), patch(
        "social_media_manager_agent.nodes.discovery.filter_eligible_movies",
        return_value=[],
    ), patch(
        "social_media_manager_agent.nodes.discovery.titles_posted_today",
        return_value=set(),
    ), patch(
        "social_media_manager_agent.nodes.discovery.broad_search"
    ) as mock_search:
        result = discover_movie_releases({"mode": "movie_release"})

    mock_search.assert_not_called()
    assert result["candidate_items"] == []
    assert result["upcoming_movies"] == []
    from social_media_manager_agent.config import get_settings

    assert result["discovery_attempt"] == get_settings().max_discovery_attempts
