from unittest.mock import patch

from social_media_manager_agent.nodes.selection import select_items
from social_media_manager_agent.schemas import CandidateItem, SelectedItem, SelectedItems


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


def test_select_items_returns_selected_items_from_state():
    fake_result = SelectedItems(
        items=[SelectedItem(title="Title A", summary="...", reason="Relevant")]
    )

    with patch(
        "social_media_manager_agent.nodes.selection.get_llm",
        return_value=_FakeLLM(fake_result),
    ):
        state = {"candidate_items": [CandidateItem(title="Title A", summary="...")]}
        result = select_items(state)

    assert result == {"selected_items": fake_result.items}


def test_select_items_dedupes_by_related_movie_title():
    fake_result = SelectedItems(
        items=[
            SelectedItem(title="Idea 1", summary="...", reason="...", related_movie_title="Movie A"),
            SelectedItem(title="Idea 2", summary="...", reason="...", related_movie_title="Movie A"),
            SelectedItem(title="Idea 3", summary="...", reason="...", related_movie_title="Movie B"),
        ]
    )

    with patch(
        "social_media_manager_agent.nodes.selection.get_llm",
        return_value=_FakeLLM(fake_result),
    ):
        state = {"candidate_items": [CandidateItem(title="Idea 1", summary="...")]}
        result = select_items(state)

    titles = [item.title for item in result["selected_items"]]
    assert titles == ["Idea 1", "Idea 3"]