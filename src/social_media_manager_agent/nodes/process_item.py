from social_media_manager_agent.models import get_llm
from social_media_manager_agent.schemas import SelectedItem
from social_media_manager_agent.tools.search import focused_search, format_results
from social_media_manager_agent.schemas import Post
from social_media_manager_agent.state import GraphState
from social_media_manager_agent.tools.storage import save_post
from datetime import date
from social_media_manager_agent.config import get_settings
from social_media_manager_agent.tools.image_gen import generate_image_bytes
from social_media_manager_agent.tools.storage import save_image, save_post


GROUNDING_PROMPT = """Your task is ONLY to gather and summarize concrete facts found in the search results.
Do NOT write a post, do NOT use emoji, do NOT use hashtags, do NOT address the audience directly.

Idea to research: "{title}" — {summary}
{movie_context}

Search results:
{search_results}

Write a bullet list (at most 5 points) of the most concrete and verifiable details found in the search
(precise dates, names, numbers, direct quotes). This text will serve as raw material for another
process that will write the actual post — it is not the post itself.
"""

WRITE_POST_PROMPT = """Write an Instagram post for a cinema, in English, based on the following facts.
You can use relevant emoji and hashtags, engaging tone — here, unlike the briefing, the final post is exactly what you want.
Base it only on the provided facts, do not invent details.

Today is {today}.

Idea: "{title}"
{movie_context}

Facts gathered from the search:
{briefing}

Choose a suitable style (e.g. Informative, Celebratory, Teaser) and a plausible publish date/time
in the next few days from today (format YYYY-MM-DDTHH:MM:SS).
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
    llm = get_llm("write_post")
    movie_context = f"Related movie: {item.related_movie_title}" if item.related_movie_title else ""
    post = llm.with_structured_output(Post).invoke(
        WRITE_POST_PROMPT.format(
            today=date.today().isoformat(),
            title=item.title,
            movie_context=movie_context,
            briefing=briefing,
        )
    )
    post.related_movie_title = item.related_movie_title
    return post

def process_item(state: GraphState) -> dict:
    item = state["selected_items"][0]
    briefing = ground_item(item)
    post = write_post(item, briefing)

    image_bytes = generate_image_bytes(post)
    image_path = save_image(image_bytes, post)
    post.image_path = str(image_path)

    save_post(post)
    return {"posts": [post]}