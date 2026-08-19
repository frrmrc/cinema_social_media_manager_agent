import csv
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from social_media_manager_agent.config import Settings, get_settings
from social_media_manager_agent.schemas import MovieRelease

logger = logging.getLogger(__name__)


def load_upcoming_movies(csv_path: Path | None = None) -> list[MovieRelease]:
    path = csv_path or get_settings().movies_csv_path
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            MovieRelease(
                title=row["title"],
                release_date=row["release_date"],
                post_count=int(row.get("post_count") or 0),
            )
            for row in reader
        ]


def filter_eligible_movies(
    movies: list[MovieRelease],
    today: date | None = None,
    settings: Settings | None = None,
) -> list[MovieRelease]:
    today = today or date.today()
    settings = settings or get_settings()
    window_start = today - timedelta(days=settings.movie_window_days_before)
    window_end = today + timedelta(days=settings.movie_window_days_after)

    eligible = []
    for movie in movies:
        try:
            release_date = datetime.fromisoformat(movie.release_date).date()
        except ValueError:
            logger.warning("Skipping movie '%s' with unparseable release_date '%s'", movie.title, movie.release_date)
            continue
        if not (window_start <= release_date <= window_end):
            continue
        if movie.post_count >= settings.max_posts_per_movie:
            continue
        eligible.append(movie)
    return eligible


def increment_post_counts(counts: dict[str, int], csv_path: Path | None = None) -> None:
    if not counts:
        return

    path = csv_path or get_settings().movies_csv_path
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if "post_count" not in fieldnames:
        fieldnames.append("post_count")

    for row in rows:
        increment = counts.get(row["title"], 0)
        if increment:
            row["post_count"] = str(int(row.get("post_count") or 0) + increment)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
