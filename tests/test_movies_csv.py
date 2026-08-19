import csv
from datetime import date, timedelta

from social_media_manager_agent.config import Settings
from social_media_manager_agent.schemas import MovieRelease
from social_media_manager_agent.tools.movies_csv import (
    filter_eligible_movies,
    increment_post_counts,
    load_upcoming_movies,
)


def _settings(**overrides):
    defaults = dict(
        openai_api_key="x",
        tavily_api_key="x",
        cinema_name="Cinema",
        post_language="it",
        cloudinary_api_key="x",
        cloudinary_api_secret="x",
        cloudinary_cloud_name="x",
        ig_user_id="x",
        ig_access_token="x",
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_load_upcoming_movies(tmp_path):
    csv_file = tmp_path / "movies.csv"
    csv_file.write_text(
        "title,release_date\n"
        "Zootropolis 2,2025-12-04\n",
        encoding="utf-8",
    )

    movies = load_upcoming_movies(csv_file)

    assert len(movies) == 1
    assert movies[0].title == "Zootropolis 2"
    assert movies[0].release_date == "2025-12-04"
    assert movies[0].post_count == 0


def test_load_upcoming_movies_reads_post_count(tmp_path):
    csv_file = tmp_path / "movies.csv"
    csv_file.write_text(
        "title,release_date,post_count\n"
        "Zootropolis 2,2025-12-04,3\n",
        encoding="utf-8",
    )

    movies = load_upcoming_movies(csv_file)

    assert movies[0].post_count == 3


def test_filter_eligible_movies_keeps_only_window():
    today = date(2026, 8, 17)
    settings = _settings(movie_window_days_before=7, movie_window_days_after=4, max_posts_per_movie=5)
    movies = [
        MovieRelease(title="TooOld", release_date=(today - timedelta(days=8)).isoformat()),
        MovieRelease(title="WindowStart", release_date=(today - timedelta(days=7)).isoformat()),
        MovieRelease(title="Today", release_date=today.isoformat()),
        MovieRelease(title="WindowEnd", release_date=(today + timedelta(days=4)).isoformat()),
        MovieRelease(title="TooFar", release_date=(today + timedelta(days=5)).isoformat()),
    ]

    result = [m.title for m in filter_eligible_movies(movies, today=today, settings=settings)]

    assert result == ["WindowStart", "Today", "WindowEnd"]


def test_filter_eligible_movies_excludes_movies_at_post_cap():
    today = date(2026, 8, 17)
    settings = _settings(max_posts_per_movie=5)
    movies = [
        MovieRelease(title="UnderCap", release_date=today.isoformat(), post_count=4),
        MovieRelease(title="AtCap", release_date=today.isoformat(), post_count=5),
    ]

    result = [m.title for m in filter_eligible_movies(movies, today=today, settings=settings)]

    assert result == ["UnderCap"]


def test_filter_eligible_movies_handles_datetime_release_dates():
    today = date(2026, 8, 17)
    settings = _settings()
    movies = [MovieRelease(title="WithTime", release_date="2026-08-19T20:30:00")]

    result = filter_eligible_movies(movies, today=today, settings=settings)

    assert len(result) == 1


def test_filter_eligible_movies_skips_unparseable_dates():
    today = date(2026, 8, 17)
    settings = _settings()
    movies = [MovieRelease(title="Bad", release_date="not-a-date")]

    result = filter_eligible_movies(movies, today=today, settings=settings)

    assert result == []


def test_increment_post_counts_updates_matching_titles(tmp_path):
    csv_file = tmp_path / "movies.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "release_date", "post_count"])
        writer.writerow(["Movie A", "2026-08-17", "1"])
        writer.writerow(["Movie B", "2026-08-18", "0"])

    increment_post_counts({"Movie A": 2}, csv_path=csv_file)

    with open(csv_file, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows[0]["post_count"] == "3"
    assert rows[1]["post_count"] == "0"


def test_increment_post_counts_adds_missing_column(tmp_path):
    csv_file = tmp_path / "movies.csv"
    csv_file.write_text("title,release_date\nMovie A,2026-08-17\n", encoding="utf-8")

    increment_post_counts({"Movie A": 1}, csv_path=csv_file)

    with open(csv_file, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows[0]["post_count"] == "1"


def test_increment_post_counts_noop_when_empty(tmp_path):
    csv_file = tmp_path / "movies.csv"
    original = "title,release_date,post_count\nMovie A,2026-08-17,0\n"
    csv_file.write_text(original, encoding="utf-8")

    increment_post_counts({}, csv_path=csv_file)

    assert csv_file.read_text(encoding="utf-8") == original
