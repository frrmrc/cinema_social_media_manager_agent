import csv
from pathlib import Path

from social_media_manager_agent.config import get_settings
from social_media_manager_agent.schemas import MovieRelease


def load_upcoming_movies(csv_path: Path | None = None) -> list[MovieRelease]:
    path = csv_path or get_settings().movies_csv_path
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            MovieRelease(
                title=row["titolo"],
                release_date=row["data_uscita"],
                screening_date=row["data_proiezione"],
            )
            for row in reader
        ]