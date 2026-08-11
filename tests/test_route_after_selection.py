from langgraph.types import Send

from social_media_manager_agent.graph import route_after_selection
from social_media_manager_agent.schemas import SelectedItem


def test_dispatches_when_items_present():
    state = {"selected_items": [SelectedItem(title="A", summary="...", reason="...")], "discovery_attempt": 1}
    result = route_after_selection(state)
    assert isinstance(result, list) and len(result) == 1


def test_retries_when_empty_and_attempts_remain():
    state = {"selected_items": [], "discovery_attempt": 1}
    assert route_after_selection(state) == "refine_query"


def test_gives_up_after_max_attempts():
    state = {"selected_items": [], "discovery_attempt": 2}
    assert route_after_selection(state) == []