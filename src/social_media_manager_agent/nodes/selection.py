from social_media_manager_agent.models import get_llm
from social_media_manager_agent.schemas import SelectedItems
from social_media_manager_agent.state import GraphState
from social_media_manager_agent.tools.history import append_to_history, format_history, load_recent_history
from social_media_manager_agent.config import get_settings

SELECTION_PROMPT = """Di seguito una lista di spunti di notizia sul mondo del cinema.
Seleziona al massimo {max_items} spunti più rilevanti per promuovere un cinema sui social media,
motivando brevemente la scelta per ciascuno. L'obiettivo è sempre quello di promuovere le nostre sale: seleziona coerentemente con questo.

NON selezionare spunti che trattano lo stesso argomento (anche con parole diverse) di uno di questi,
già pubblicati negli ultimi {history_days} giorni:
{history}

Spunti disponibili:
{candidates}

Se NESSUNO spunto disponibile è utilizzabile perché tutti coincidono con argomenti già trattati,
ritorna una lista vuota.
"""



def _format_candidates(candidates) -> str:
    return "\n\n".join(
        f"- {c.title}\n  {c.summary}"
        + (f"\n  (film collegato: {c.related_movie_title})" if c.related_movie_title else "")
        for c in candidates
    )


def select_items(state: GraphState) -> dict:
    settings = get_settings()
    history = load_recent_history(days=settings.history_window_days)
    llm = get_llm("select_items")
    selection = llm.with_structured_output(SelectedItems).invoke(
        SELECTION_PROMPT.format(
            max_items=settings.max_posts_per_run,
            history_days=settings.history_window_days,
            history=format_history(history),
            candidates=_format_candidates(state["candidate_items"]),
        )
    )
    items = selection.items[: settings.max_posts_per_run]
    append_to_history(items)
    return {"selected_items": items}