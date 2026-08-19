from unittest.mock import MagicMock, patch

import pytest
import requests

from social_media_manager_agent.tools.instagram import (
    _create_media_container,
    _publish_media_container,
    _raise_for_status_with_body,
    _wait_until_container_ready,
    publish_image_post,
)


def _fake_response(json_data):
    response = MagicMock()
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


def _fake_error_response(status_code, error_body):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = error_body
    response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        f"{status_code} Client Error", response=response
    )
    return response


def test_create_media_container_returns_creation_id():
    fake_response = _fake_response({"id": "creation-123"})
    with patch("social_media_manager_agent.tools.instagram.requests.post", return_value=fake_response):
        creation_id = _create_media_container("https://example.com/img.png", "caption")

    assert creation_id == "creation-123"


def test_publish_media_container_returns_media_id():
    fake_response = _fake_response({"id": "media-456"})
    with patch("social_media_manager_agent.tools.instagram.requests.post", return_value=fake_response):
        media_id = _publish_media_container("creation-123")

    assert media_id == "media-456"


def test_wait_until_container_ready_polls_until_finished():
    responses = [
        _fake_response({"status_code": "IN_PROGRESS"}),
        _fake_response({"status_code": "FINISHED"}),
    ]
    with patch("social_media_manager_agent.tools.instagram.requests.get", side_effect=responses), \
         patch("social_media_manager_agent.tools.instagram.time.sleep"):
        _wait_until_container_ready("creation-123")


def test_wait_until_container_ready_raises_on_error_status():
    fake_response = _fake_response({"status_code": "ERROR"})
    with patch("social_media_manager_agent.tools.instagram.requests.get", return_value=fake_response), \
         patch("social_media_manager_agent.tools.instagram.time.sleep"):
        with pytest.raises(RuntimeError):
            _wait_until_container_ready("creation-123")


def test_raise_for_status_with_body_includes_graph_api_error_detail():
    error_body = {"error": {"message": "Invalid parameter", "type": "OAuthException", "code": 100}}
    fake_response = _fake_error_response(400, error_body)

    with pytest.raises(requests.exceptions.HTTPError) as exc_info:
        _raise_for_status_with_body(fake_response)

    assert "Invalid parameter" in str(exc_info.value)


def test_raise_for_status_with_body_passes_through_on_success():
    fake_response = _fake_response({"id": "creation-123"})

    _raise_for_status_with_body(fake_response)  # should not raise


def test_publish_image_post_orchestrates_full_flow():
    with patch(
        "social_media_manager_agent.tools.instagram._create_media_container", return_value="creation-123"
    ) as mock_create, patch(
        "social_media_manager_agent.tools.instagram._wait_until_container_ready"
    ) as mock_wait, patch(
        "social_media_manager_agent.tools.instagram._publish_media_container", return_value="media-456"
    ) as mock_publish:
        media_id = publish_image_post("https://example.com/img.png", "caption")

    assert media_id == "media-456"
    mock_create.assert_called_once_with("https://example.com/img.png", "caption")
    mock_wait.assert_called_once_with("creation-123")
    mock_publish.assert_called_once_with("creation-123")
