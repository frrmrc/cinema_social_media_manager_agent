from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from social_media_manager_agent.config import get_settings

IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def upload_image_to_imgbb(image_path: Path) -> str:
    settings = get_settings()
    with open(image_path, "rb") as image_file:
        response = requests.post(
            IMGBB_UPLOAD_URL,
            data={"key": settings.imgbb_api_key, "expiration": settings.imgbb_expiration_seconds},
            files={"image": image_file},
            timeout=60,
        )
    response.raise_for_status()
    return response.json()["data"]["url"]
