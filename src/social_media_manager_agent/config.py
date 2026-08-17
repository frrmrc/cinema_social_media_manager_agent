from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    openai_api_key: str
    tavily_api_key: str

    cinema_name: str
    post_language: str

    default_model: str = "gpt-4o-mini"
    save_folder: Path = Path("output/posts")
    movies_csv_path: Path = Path("data/movies.csv")
    history_path: Path = Path("data/history.json")
    max_discovery_attempts: int = 2
    max_posts_per_run: int = 3
    broad_search_results: int = 10
    movie_search_results: int = 6
    focused_search_results: int = 4
    history_window_days: int = 15

    brand_template_path: Path = Path("data/brand_template.png")
    images_folder: Path = Path("output/images")
    log_path: Path = Path("output/agent.log")

    image_model: str = "gpt-image-2"
    image_size: str = "1024x1024"
    image_quality: str = "low"

    imgbb_api_key: str
    # imgbb silently disables expiration (treats it as "never expire") for values outside
    # its documented 60-15552000 range, instead of rejecting the request.
    imgbb_expiration_seconds: int = Field(default=600, ge=60, le=15552000)
    ig_user_id: str
    ig_access_token: str
    graph_api_version: str = "v21.0"

def get_settings() -> Settings:
    return Settings()