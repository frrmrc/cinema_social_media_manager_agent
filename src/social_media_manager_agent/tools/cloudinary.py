import hashlib
import time
from pathlib import Path
from typing import NamedTuple

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from social_media_manager_agent.config import get_settings

CLOUDINARY_UPLOAD_URL = "https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
CLOUDINARY_DESTROY_URL = "https://api.cloudinary.com/v1_1/{cloud_name}/image/destroy"


class CloudinaryUpload(NamedTuple):
    url: str
    public_id: str


def _sign_params(params: dict, api_secret: str) -> str:
    to_sign = "&".join(f"{key}={value}" for key, value in sorted(params.items()))
    return hashlib.sha1(f"{to_sign}{api_secret}".encode("utf-8")).hexdigest()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def upload_image_to_cloudinary(image_path: Path) -> CloudinaryUpload:
    settings = get_settings()
    timestamp = int(time.time())
    signature = _sign_params({"timestamp": timestamp}, settings.cloudinary_api_secret)

    url = CLOUDINARY_UPLOAD_URL.format(cloud_name=settings.cloudinary_cloud_name)
    with open(image_path, "rb") as image_file:
        response = requests.post(
            url,
            data={
                "api_key": settings.cloudinary_api_key,
                "timestamp": timestamp,
                "signature": signature,
            },
            files={"file": image_file},
            timeout=60,
        )
    response.raise_for_status()
    data = response.json()
    return CloudinaryUpload(url=data["secure_url"], public_id=data["public_id"])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def delete_image_from_cloudinary(public_id: str) -> dict:
    settings = get_settings()
    timestamp = int(time.time())
    signature = _sign_params({"public_id": public_id, "timestamp": timestamp}, settings.cloudinary_api_secret)

    url = CLOUDINARY_DESTROY_URL.format(cloud_name=settings.cloudinary_cloud_name)
    response = requests.post(
        url,
        data={
            "public_id": public_id,
            "api_key": settings.cloudinary_api_key,
            "timestamp": timestamp,
            "signature": signature,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def wait_until_publicly_reachable(url: str, max_attempts: int = 5, wait_seconds: float = 2.0) -> None:
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image/"):
                return
        except requests.exceptions.RequestException:
            pass

        if attempt < max_attempts - 1:
            time.sleep(wait_seconds)

    raise RuntimeError(f"Cloudinary URL {url} not publicly reachable after {max_attempts} attempts")
