import hashlib
from unittest.mock import MagicMock, patch

import pytest
import requests

from social_media_manager_agent.tools.cloudinary import (
    delete_image_from_cloudinary,
    upload_image_to_cloudinary,
    wait_until_publicly_reachable,
)


def _fake_response(json_data, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


def _fake_get_response(status_code=200, content_type="image/png"):
    response = MagicMock()
    response.status_code = status_code
    response.headers = {"Content-Type": content_type}
    return response


def test_upload_image_to_cloudinary_returns_secure_url(tmp_path):
    image_path = tmp_path / "post.png"
    image_path.write_bytes(b"fake-image-bytes")

    fake_response = _fake_response(
        {"secure_url": "https://res.cloudinary.com/demo/image/upload/abc/post.png", "public_id": "abc/post"}
    )

    with patch("social_media_manager_agent.tools.cloudinary.requests.post", return_value=fake_response) as mock_post:
        result = upload_image_to_cloudinary(image_path)

    assert result.url == "https://res.cloudinary.com/demo/image/upload/abc/post.png"
    assert result.public_id == "abc/post"
    assert mock_post.call_count == 1
    sent_data = mock_post.call_args.kwargs["data"]
    assert "api_key" in sent_data
    assert "timestamp" in sent_data
    assert "signature" in sent_data


def test_upload_image_to_cloudinary_signs_only_timestamp():
    from social_media_manager_agent.tools.cloudinary import _sign_params

    expected = hashlib.sha1(b"timestamp=1000secret").hexdigest()
    assert _sign_params({"timestamp": 1000}, "secret") == expected


def test_sign_params_sorts_multiple_keys_alphabetically():
    from social_media_manager_agent.tools.cloudinary import _sign_params

    expected = hashlib.sha1(b"public_id=x&timestamp=1000secret").hexdigest()
    assert _sign_params({"timestamp": 1000, "public_id": "x"}, "secret") == expected


def test_upload_image_to_cloudinary_retries_on_transient_failure(tmp_path):
    image_path = tmp_path / "post.png"
    image_path.write_bytes(b"fake-image-bytes")

    fake_response = _fake_response(
        {"secure_url": "https://res.cloudinary.com/demo/image/upload/abc/post.png", "public_id": "abc/post"}
    )

    with patch(
        "social_media_manager_agent.tools.cloudinary.requests.post",
        side_effect=[ConnectionError("boom"), fake_response],
    ) as mock_post:
        result = upload_image_to_cloudinary(image_path)

    assert result.url == "https://res.cloudinary.com/demo/image/upload/abc/post.png"
    assert mock_post.call_count == 2


def test_delete_image_from_cloudinary_sends_signed_destroy_request():
    fake_response = _fake_response({"result": "ok"})

    with patch("social_media_manager_agent.tools.cloudinary.requests.post", return_value=fake_response) as mock_post:
        result = delete_image_from_cloudinary("abc/post")

    assert result == {"result": "ok"}
    assert mock_post.call_count == 1
    call_url = mock_post.call_args.args[0]
    assert call_url.endswith("/image/destroy")
    sent_data = mock_post.call_args.kwargs["data"]
    assert sent_data["public_id"] == "abc/post"
    assert "api_key" in sent_data
    assert "timestamp" in sent_data
    assert "signature" in sent_data


def test_delete_image_from_cloudinary_retries_on_transient_failure():
    fake_response = _fake_response({"result": "ok"})

    with patch(
        "social_media_manager_agent.tools.cloudinary.requests.post",
        side_effect=[ConnectionError("boom"), fake_response],
    ) as mock_post:
        result = delete_image_from_cloudinary("abc/post")

    assert result == {"result": "ok"}
    assert mock_post.call_count == 2


def test_wait_until_publicly_reachable_succeeds_first_try():
    fake_response = _fake_get_response()

    with patch("social_media_manager_agent.tools.cloudinary.requests.get", return_value=fake_response) as mock_get, \
         patch("social_media_manager_agent.tools.cloudinary.time.sleep") as mock_sleep:
        wait_until_publicly_reachable("https://res.cloudinary.com/demo/image/upload/abc/post.png")

    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


def test_wait_until_publicly_reachable_succeeds_after_retries():
    responses = [
        _fake_get_response(status_code=404),
        _fake_get_response(status_code=200, content_type="text/html"),
        _fake_get_response(status_code=200, content_type="image/png"),
    ]

    with patch("social_media_manager_agent.tools.cloudinary.requests.get", side_effect=responses) as mock_get, \
         patch("social_media_manager_agent.tools.cloudinary.time.sleep") as mock_sleep:
        wait_until_publicly_reachable("https://res.cloudinary.com/demo/image/upload/abc/post.png")

    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2


def test_wait_until_publicly_reachable_retries_on_request_exception():
    responses = [requests.exceptions.ConnectionError("boom"), _fake_get_response()]

    with patch("social_media_manager_agent.tools.cloudinary.requests.get", side_effect=responses) as mock_get, \
         patch("social_media_manager_agent.tools.cloudinary.time.sleep"):
        wait_until_publicly_reachable("https://res.cloudinary.com/demo/image/upload/abc/post.png")

    assert mock_get.call_count == 2


def test_wait_until_publicly_reachable_raises_after_exhausting_attempts():
    fake_response = _fake_get_response(status_code=404)

    with patch("social_media_manager_agent.tools.cloudinary.requests.get", return_value=fake_response) as mock_get, \
         patch("social_media_manager_agent.tools.cloudinary.time.sleep"):
        with pytest.raises(RuntimeError):
            wait_until_publicly_reachable("https://res.cloudinary.com/demo/image/upload/abc/post.png", max_attempts=3)

    assert mock_get.call_count == 3
