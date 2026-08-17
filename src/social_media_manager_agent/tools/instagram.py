import logging
import time

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from social_media_manager_agent.config import get_settings

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.instagram.com"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _create_media_container(image_url: str, caption: str) -> str:
    settings = get_settings()
    url = f"{GRAPH_API_BASE}/{settings.graph_api_version}/{settings.ig_user_id}/media"
    response = requests.post(
        url,
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": settings.ig_access_token,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["id"]


def _wait_until_container_ready(creation_id: str, max_attempts: int = 5, wait_seconds: int = 3) -> None:
    settings = get_settings()
    url = f"{GRAPH_API_BASE}/{settings.graph_api_version}/{creation_id}"
    for attempt in range(max_attempts):
        response = requests.get(
            url,
            params={"fields": "status_code", "access_token": settings.ig_access_token},
            timeout=30,
        )
        response.raise_for_status()
        status = response.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Instagram media container {creation_id} failed processing")
        if attempt < max_attempts - 1:
            time.sleep(wait_seconds)
    raise TimeoutError(f"Instagram media container {creation_id} not ready after {max_attempts} attempts")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _publish_media_container(creation_id: str) -> str:
    settings = get_settings()
    url = f"{GRAPH_API_BASE}/{settings.graph_api_version}/{settings.ig_user_id}/media_publish"
    response = requests.post(
        url,
        data={
            "creation_id": creation_id,
            "access_token": settings.ig_access_token,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["id"]


def publish_image_post(image_url: str, caption: str) -> str:
    creation_id = _create_media_container(image_url, caption)
    _wait_until_container_ready(creation_id)
    return _publish_media_container(creation_id)
