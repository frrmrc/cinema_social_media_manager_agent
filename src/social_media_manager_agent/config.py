from pathlib import Path

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
    movie_window_days_before: int = 7  # how many days after release a movie is still considered "eligible"
    movie_window_days_after: int = 4  # how many days before release a movie starts being considered
    max_posts_per_movie: int = 5  # max approved posts ever generated for a single movie
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

    cloudinary_api_key: str
    cloudinary_api_secret: str
    cloudinary_cloud_name: str
    ig_user_id: str
    ig_access_token: str
    graph_api_version: str = "v21.0"

def get_settings() -> Settings:
    return Settings()