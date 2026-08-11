from social_media_manager_agent.models import get_llm
from social_media_manager_agent.schemas import CandidateItems, CandidateItem
from social_media_manager_agent.state import GraphState
from social_media_manager_agent.tools.search import broad_search
from social_media_manager_agent.tools.movies_csv import load_upcoming_movies
from social_media_manager_agent.tools.search import broad_search, format_results
from social_media_manager_agent.tools.history import format_history, load_recent_history
from social_media_manager_agent.config import get_settings


GENERIC_NEWS_QUERY = "movie news and trivia this week"

EXTRACTION_PROMPT = """Below is a series of search results about the movie world.
Extract up to 8 distinct, relevant news ideas, each with a short title and brief summary.

Search results:
{search_results}
"""

MOVIE_NEWS_QUERY_TEMPLATE = "news, reviews and trivia about '{title}' theatrical release {release_date}"

MOVIE_EXTRACTION_PROMPT = """Below is a series of search results about the movie "{title}" (release: {release_date}).
Extract up to 3 distinct, relevant news ideas for a social post, each with a short title and brief summary.

Search results:
{search_results}
"""

REFINE_QUERY_PROMPT = """All the ideas found in the last search correspond to topics already covered
in recently published posts (listed below). Suggest, in a single sentence, a different search angle
to find fresh movie-world news, avoiding these topics.

Topics already covered recently:
{history}

Reply only with the search direction (one sentence), nothing else.
"""




def discover_generic_news(state: GraphState) -> dict:
    hint = state.get("search_hint")
    query = GENERIC_NEWS_QUERY if not hint else f"{GENERIC_NEWS_QUERY}. {hint}"

    settings = get_settings()
    results = broad_search(query, max_results=settings.broad_search_results)

    prompt = EXTRACTION_PROMPT.format(search_results=format_results(results))
    if hint:
        prompt += f"\n\nAvoid ideas related to: {hint}"

    llm = get_llm("discover_generic_news")
    extraction = llm.with_structured_output(CandidateItems).invoke(prompt)

    return {
        "candidate_items": extraction.items,
        "discovery_attempt": state.get("discovery_attempt", 0) + 1,
    }


def discover_movie_releases(state: GraphState) -> dict:
    settings = get_settings()

    movies = load_upcoming_movies()
    hint = state.get("search_hint")
    llm = get_llm("discover_movie_releases")
    all_candidates: list[CandidateItem] = []

    for movie in movies:
        query = MOVIE_NEWS_QUERY_TEMPLATE.format(title=movie.title, release_date=movie.release_date)
        if hint:
            query = f"{query}. {hint}"
        results = broad_search(query, max_results=settings.movie_search_results)

        prompt = MOVIE_EXTRACTION_PROMPT.format(
            title=movie.title, release_date=movie.release_date, search_results=format_results(results)
        )
        if hint:
            prompt += f"\n\nAvoid ideas related to: {hint}"

        extraction = llm.with_structured_output(CandidateItems).invoke(prompt)
        for item in extraction.items:
            item.related_movie_title = movie.title
        all_candidates.extend(extraction.items)

    return {
        "candidate_items": all_candidates,
        "upcoming_movies": movies,
        "discovery_attempt": state.get("discovery_attempt", 0) + 1,
    }

def route_discovery(state: GraphState) -> str:
    if state["mode"] == "movie_release":
        return "discover_movie_releases"
    return "discover_generic_news"



def refine_query(state: GraphState) -> dict:
    history = load_recent_history(days=get_settings().history_window_days)
    llm = get_llm("refine_query")
    hint = llm.invoke(REFINE_QUERY_PROMPT.format(history=format_history(history))).content
    return {"search_hint": hint}
