from unittest.mock import patch

from social_media_manager_agent.nodes.process_item import write_post
from social_media_manager_agent.schemas import DraftPost, SelectedItem


class _FakeStructuredLLM:
    def __init__(self, result):
        self._result = result
        self.received_schema = None

    def invoke(self, prompt):
        return self._result


class _FakeLLM:
    def __init__(self, result):
        self._result = result
        self.requested_schema = None

    def with_structured_output(self, schema):
        self.requested_schema = schema
        return _FakeStructuredLLM(self._result)


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
