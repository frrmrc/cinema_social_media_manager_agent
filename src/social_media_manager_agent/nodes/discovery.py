from social_media_manager_agent.models import get_llm
from social_media_manager_agent.schemas import CandidateItems, CandidateItem
from social_media_manager_agent.state import GraphState
from social_media_manager_agent.tools.movies_csv import filter_eligible_movies, load_upcoming_movies
from social_media_manager_agent.tools.search import broad_search, format_results
from social_media_manager_agent.tools.history import format_history, load_recent_history, titles_posted_today
from social_media_manager_agent.config import get_settings


GENERIC_NEWS_QUERY = (
    "cinema industry news this week: new films, industry rumors and leaks, "
    "actor and director news, award and cast updates, box office records, film festivals, "
    "cinema tech like IMAX Dolby AI VFX, industry partnerships, viral entertainment news"
)

EXTRACTION_PROMPT = """Below is a series of search results with news related to the cinema industry.

Your findings will be used to create social media content that promotes {cinema_name}, not just movies.
Extract up to 8 distinct, relevant news ideas covering things like:
- new movies
- Rumors, leaks, industry scoops
- News about actors, directors, awards, and cast updates
- Industry trends
- Emerging tech (IMAX, Dolby, AI, VFX, etc.)
- Box office records
- Events, festivals, partnerships
- Viral and audience-relevant entertainment news

For each idea, give a short title and brief summary.

Search results:
{search_results}
"""

MOVIE_NEWS_QUERY_TEMPLATE = "news, reviews, cast, teasers, breaking news, actors, gossip about '{title}',  release date: {release_date}"

MOVIE_EXTRACTION_PROMPT = """Below is a series of search results about the movie "{title}" (release: {release_date}).
Extract up to 3 distinct, relevant news ideas for a social media post, each with a short title and brief summary.

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

    prompt = EXTRACTION_PROMPT.format(cinema_name=settings.cinema_name, search_results=format_results(results))
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
    eligible = filter_eligible_movies(movies, settings=settings)
    already_posted_today = titles_posted_today()
    movies = [m for m in eligible if m.title not in already_posted_today]

    if not movies:
        return {
            "candidate_items": [],
            "upcoming_movies": [],
            "discovery_attempt": settings.max_discovery_attempts,
        }

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
