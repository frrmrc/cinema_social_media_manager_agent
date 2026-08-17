import logging

from social_media_manager_agent.models import get_llm
from social_media_manager_agent.schemas import SelectedItem
from social_media_manager_agent.tools.search import focused_search, format_results
from social_media_manager_agent.schemas import DraftPost, Post
from social_media_manager_agent.state import GraphState
from social_media_manager_agent.tools.storage import save_post
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

Include a clear call-to-action inviting the audience to visit {cinema_name}, it is not mandatory that the call to action is consistent with the topic of the post.

The goal of the post is to keep our community engaged with interesting news about the cinema world. The goal is not to promote movies now playing in out theaters.  
Today is {today}.

Idea: "{title}"
{movie_context}

Facts gathered from the search:
{briefing}

Choose a suitable style (e.g. Informative, Celebratory, Teaser, Gossip).
"""




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

def write_post(item: SelectedItem, briefing: str) -> Post:
    settings = get_settings()
    llm = get_llm("write_post")
    movie_context = f"Related movie: {item.related_movie_title}" if item.related_movie_title else ""
    draft = llm.with_structured_output(DraftPost).invoke(
        WRITE_POST_PROMPT.format(
            cinema_name=settings.cinema_name,
            post_language=settings.post_language,
            today=date.today().isoformat(),
            title=item.title,
            movie_context=movie_context,
            briefing=briefing,
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
    try:
        briefing = ground_item(item)
        post = write_post(item, briefing)

        image_bytes = generate_image_bytes(post)
        if image_bytes is not None:
            image_path = save_image(image_bytes, post)
            post.image_path = str(image_path)

        save_post(post)
        return {"posts": [post]}
    except Exception:
        logger.warning("Skipping item '%s'", item.title, exc_info=True)
        return {"posts": [], "skipped_items": [item.title]}