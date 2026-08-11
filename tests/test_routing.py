from social_media_manager_agent.nodes.discovery import route_discovery


def test_route_discovery_generic_news():
    assert route_discovery({"mode": "generic_news"}) == "discover_generic_news"


def test_route_discovery_movie_release():
    assert route_discovery({"mode": "movie_release"}) == "discover_movie_releases"