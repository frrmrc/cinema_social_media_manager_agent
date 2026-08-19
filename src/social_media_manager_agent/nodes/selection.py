from social_media_manager_agent.models import get_llm
from social_media_manager_agent.schemas import SelectedItems
from social_media_manager_agent.state import GraphState
from social_media_manager_agent.tools.history import append_to_history, format_history, load_recent_history
from social_media_manager_agent.config import get_settings

SELECTION_PROMPT = """Below is a list of news ideas about the movie world.
Select at most {max_items} of the most relevant ideas for promoting a cinema on social media,
briefly explaining the reasoning for each. The goal is to keep our customers engaged with the cinema world and promote our theaters: select consistently with this.

Do NOT select news and information regarding offers, discounts, prices, ticket sales, promotions, or other purely commercial matters. Prefer editorially relevant cinema news over transactional content.
DO NOT select ideas that cover the same topic (even with different wording) as any of these,
already published in the last {history_days} days. NEVER select ideas that cover these topics:
{history}



Available ideas:
{candidates}

If NO available idea is usable because they all overlap with already-covered topics,
return an empty list.
"""



def _format_candidates(candidates) -> str:
    return "\n\n".join(
        f"- {c.title}\n  {c.summary}"
        + (f"\n  (related movie: {c.related_movie_title})" if c.related_movie_title else "")
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
    items = _dedupe_by_movie(selection.items)[: settings.max_posts_per_run]
    append_to_history(items)
    return {"selected_items": items}


def _dedupe_by_movie(items):
    seen: set[str] = set()
    deduped = []
    for item in items:
        key = item.related_movie_title
        if key is not None:
            if key in seen:
                continue
            seen.add(key)
        deduped.append(item)
    return deduped