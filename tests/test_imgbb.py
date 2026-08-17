from unittest.mock import MagicMock, patch

from social_media_manager_agent.tools.imgbb import upload_image_to_imgbb


def _fake_response(json_data, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


def test_upload_image_to_imgbb_returns_url(tmp_path):
    image_path = tmp_path / "post.png"
    image_path.write_bytes(b"fake-image-bytes")

    fake_response = _fake_response({"data": {"url": "https://i.ibb.co/abc/post.png"}})

    with patch("social_media_manager_agent.tools.imgbb.requests.post", return_value=fake_response) as mock_post:
        url = upload_image_to_imgbb(image_path)

    assert url == "https://i.ibb.co/abc/post.png"
    assert mock_post.call_count == 1
    assert "expiration" in mock_post.call_args.kwargs["data"]


def test_upload_image_to_imgbb_retries_on_transient_failure(tmp_path):
    image_path = tmp_path / "post.png"
    image_path.write_bytes(b"fake-image-bytes")

    fake_response = _fake_response({"data": {"url": "https://i.ibb.co/abc/post.png"}})

    with patch(
        "social_media_manager_agent.tools.imgbb.requests.post",
        side_effect=[ConnectionError("boom"), fake_response],
    ) as mock_post:
        url = upload_image_to_imgbb(image_path)

    assert url == "https://i.ibb.co/abc/post.png"
    assert mock_post.call_count == 2
