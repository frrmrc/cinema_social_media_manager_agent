import operator
from typing import Annotated, Literal

from typing_extensions import TypedDict

from social_media_manager_agent.schemas import CandidateItem, MovieRelease, Post, SelectedItem


class GraphState(TypedDict):
    mode: Literal["generic_news", "movie_release"]
    upcoming_movies: list[MovieRelease]
    candidate_items: list[CandidateItem]
    selected_items: list[SelectedItem]
    discovery_attempt: int
    search_hint: str | None
    posts: Annotated[list[Post], operator.add]