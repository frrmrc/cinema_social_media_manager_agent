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


GROUNDING_PROMPT = """Il tuo compito è SOLO raccogliere e riassumere fatti concreti trovati nella ricerca.
NON scrivere un post, NON usare emoji, NON usare hashtag, NON rivolgerti al pubblico direttamente.

Spunto da approfondire: "{title}" — {summary}
{movie_context}

Risultati di ricerca:
{search_results}

Scrivi un elenco puntato (massimo 5 punti) dei dettagli più concreti e verificabili trovati nella ricerca
(date precise, nomi, numeri, citazioni dirette). Questo testo servirà come materiale grezzo per un altro
processo che scriverà il post vero e proprio — non è il post stesso.
"""

WRITE_POST_PROMPT = """Scrivi un post Instagram per un cinema, in italiano, basato sui fatti seguenti.
Puoi usare emoji e hashtag pertinenti, tono coinvolgente — qui, a differenza del briefing, il post finale è proprio quello che vuoi.
Basati solo sui fatti forniti, non inventare dettagli.

Oggi è {today}.

Spunto: "{title}"
{movie_context}

Fatti raccolti dalla ricerca:
{briefing}

Scegli uno stile adatto (es. Informativo, Celebrativo, Teaser) e una data/ora di pubblicazione plausibile
nei prossimi giorni rispetto a oggi (formato YYYY-MM-DDTHH:MM:SS).
"""




def ground_item(item: SelectedItem) -> str:
    settings = get_settings()
    query = f"{item.title} {item.summary}"
    results = focused_search(query, settings.focused_search_results)

    movie_context = f"Film collegato: {item.related_movie_title}" if item.related_movie_title else ""
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
    movie_context = f"Film collegato: {item.related_movie_title}" if item.related_movie_title else ""
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