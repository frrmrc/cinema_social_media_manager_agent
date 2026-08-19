import logging

from social_media_manager_agent.models import get_llm
from social_media_manager_agent.schemas import SelectedItem
from social_media_manager_agent.tools.search import focused_search, format_results
from social_media_manager_agent.schemas import DraftPost, MovieRelease, Post
from social_media_manager_agent.state import GraphState
from datetime import date
from social_media_manager_agent.config import get_settings
from social_media_manager_agent.tools.image_gen import generate_image_bytes
from social_media_manager_agent.tools.storage import save_image, save_post

logger = logging.getLogger(__name__)


GROUNDING_PROMPT = """Your task is ONLY to gather concrete facts found in the search results.
Do NOT write a post, do NOT use emoji, do NOT use hashtags, do NOT address the audience directly.

Idea to research: "{title}" — {summary}
{movie_context}

Search results:
{search_results}

Write a bullet list (at most 5 points) of the most concrete and verifiable details found in the search
(precise dates, names, numbers, direct quotes). This text will serve as raw material for another
process that will write the actual post — it is not the post itself.

If the search results do not contain concrete, verifiable details (exact dates, times, prices, names,
numbers, direct quotes), say so explicitly instead of leaving room for guessing — e.g. "No specific
verifiable details found beyond the general idea." Do not fill gaps with plausible-sounding assumptions.
"""

WRITE_POST_PROMPT = """Write an Instagram post for {cinema_name}, in {post_language}, based on the following facts.
You can use relevant emoji and hashtags, engaging tone.

Use ONLY the facts listed below. Do not invent dates, times, prices, names, quotes, or example content
(e.g. do not make up quiz questions, schedules, or trivia facts if none are given in the briefing) — if a
detail isn't in the facts, phrase the post more generally instead (e.g. "join our regular movie nights"
rather than inventing "every Thursday at 7 PM"). Always refer to the cinema as "{cinema_name}", never a
placeholder like "[Cinema Name]".

Lead with the facts that make the film exciting to watch (the hook, cast/director, why it's generating
buzz) — that's what should carry the post. For secondary, hard-to-pin-down details the briefing may contain
(exact release dates in other countries, precise festival categories, technical cinematography credits),
reference them loosely instead of as precise figures (e.g. "already creating buzz abroad" rather than naming
a specific foreign release date) — precision on those isn't the point of the post.

Include a clear call-to-action inviting the audience to visit {cinema_name}, it is not mandatory that the call to action is consistent with the topic of the post.

{mode_note}
Today is {today}.

Idea: "{title}"
{movie_context}

Facts gathered from the search:
{briefing}

Choose a suitable style (e.g. Informative, Celebratory, Teaser, Gossip).

Do not format the output with italic, bold, etc using asterisks or other symbols.
"""

GENERIC_NEWS_MODE_NOTE = (
    "This idea is general cinema-industry news, not necessarily a movie {cinema_name} is screening. The goal "
    "of THIS post is to keep our community engaged with interesting news about the cinema world in general, "
    "not to promote a specific screening — do not imply {cinema_name} is showing this movie unless the facts "
    "say so."
)


def _movie_release_mode_note(cinema_name: str, movie_title: str, release_date: str | None) -> str:
    date_clause = f", starting {release_date}" if release_date else ""
    must_mention = (
        f'clearly mention the movie title "{movie_title}" and that it\'s coming to / it\'s available at {cinema_name}{date_clause} based on today\'s date {date.today().isoformat()}'
        if release_date
        else f'clearly mention the movie title "{movie_title}"'
    )
    return (
        f'This post is specifically about the movie "{movie_title}", which {cinema_name} is actually '
        f'screening{date_clause} (confirmed, from our own lineup). The goal of THIS post is to promote '
        f'"{movie_title}" and make people want to come watch it at {cinema_name}: build curiosity around it, '
        f'lead with the most interesting news/trivia/gossip about it, and make the film itself the hook of the '
        f'post. The post MUST {must_mention}. '
        f'Never write information about availability of the movie on streaming and streaming platforms brands like Netflix, '
        f'Disney+, Prime, etc. Never give information about streaming. period.'
        f'Skip completly the country-availability topic: never give information about the countries where the movie is available ( like USA, United Kingdom, Mexico, India, etc.). '
        f' do not say something like "U.S. release date: August 21, 2026." or "Available in Germany from January 15, 2027" '
    )




def ground_item(item: SelectedItem) -> str:
    settings = get_settings()
    query = f"{item.title} {item.summary}"
    results = focused_search(query, settings.focused_search_results)

    movie_context = f"Related movie: {item.related_movie_title}" if item.related_movie_title else ""
    llm = get_llm("ground_item")
    briefing = llm.invoke(
        GROUNDING_PROMPT.format(
            title=item.title,
            summary=item.summary,
            movie_context=movie_context,
            search_results=format_results(results),
        )
    )
    return briefing.content

def _find_movie(title: str | None, movies: list[MovieRelease]) -> MovieRelease | None:
    if not title:
        return None
    for movie in movies:
        if movie.title == title:
            return movie
    return None


def write_post(item: SelectedItem, briefing: str, mode: str | None = None, movie: MovieRelease | None = None) -> Post:
    settings = get_settings()
    llm = get_llm("write_post")

    if mode == "movie_release":
        movie_title = movie.title if movie else item.related_movie_title
        release_date = movie.release_date if movie else None
        movie_context = f"Related movie: {movie_title}"
        if release_date:
            movie_context += f" (release date: {release_date})"
        mode_note = _movie_release_mode_note(settings.cinema_name, movie_title or "this movie", release_date)
    else:
        movie_context = f"Related movie: {item.related_movie_title}" if item.related_movie_title else ""
        mode_note = GENERIC_NEWS_MODE_NOTE.format(cinema_name=settings.cinema_name)

    draft = llm.with_structured_output(DraftPost).invoke(
        WRITE_POST_PROMPT.format(
            cinema_name=settings.cinema_name,
            post_language=settings.post_language,
            today=date.today().isoformat(),
            title=item.title,
            movie_context=movie_context,
            briefing=briefing,
            mode_note=mode_note,
        )
    )
    return Post(
        title=draft.title,
        body=draft.body,
        style=draft.style,
        related_movie_title=item.related_movie_title,
    )

def process_item(state: GraphState) -> dict:
    item = state["selected_items"][0]
    mode = state.get("mode")
    movie = _find_movie(item.related_movie_title, state.get("upcoming_movies", []))
    try:
        briefing = ground_item(item)
        post = write_post(item, briefing, mode, movie)

        image_bytes = generate_image_bytes(post)
        if image_bytes is not None:
            image_path = save_image(image_bytes, post)
            post.image_path = str(image_path)

        save_post(post)
        return {"posts": [post]}
    except Exception:
        logger.warning("Skipping item '%s'", item.title, exc_info=True)
        return {"posts": [], "skipped_items": [item.title]}