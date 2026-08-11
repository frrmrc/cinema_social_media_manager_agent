from social_media_manager_agent.tools.movies_csv import load_upcoming_movies


def test_load_upcoming_movies(tmp_path):
    csv_file = tmp_path / "movies.csv"
    csv_file.write_text(
        "title,release_date,screening_date\n"
        "Zootropolis 2,2025-12-04,2025-12-04T20:30:00\n",
        encoding="utf-8",
    )

    movies = load_upcoming_movies(csv_file)

    assert len(movies) == 1
    assert movies[0].title == "Zootropolis 2"
    assert movies[0].release_date == "2025-12-04"
    assert movies[0].screening_date == "2025-12-04T20:30:00"