import logging

from social_media_manager_agent.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    settings.log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(settings.log_path, encoding="utf-8"),
        ],
    )
