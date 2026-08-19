import logging
from collections import Counter

from social_media_manager_agent.config import get_settings
from social_media_manager_agent.models import get_llm
from social_media_manager_agent.schemas import PostReviews
from social_media_manager_agent.state import GraphState
from social_media_manager_agent.tools.movies_csv import increment_post_counts
from social_media_manager_agent.tools.storage import save_post
from datetime import date

logger = logging.getLogger(__name__)


REVIEW_PROMPT = """You are the final reviewer for {cinema_name}'s Instagram account, scheduling today's
batch of {count} generated posts. Today is {today}.

For each post, decide:
- Whether it is ready to be published as-is, with no further human review. Default to approving it — only
  reject for a concrete, specific problem: placeholder text (e.g. "[Cinema Name]", "TBD", "lorem ipsum"), a
  tone or content inappropriate for a public brand account, content clearly off-topic for a cinema's social
  media presence, or an invented fact that is central to what we're promising the audience (an exact price,
  an exact showtime at {cinema_name}, or something stated as guaranteed when it's clearly speculative).
  Secondary color details drawn from the briefing — trivia, festival mentions, background quotes, release
  buzz from other countries — are expected for this kind of post and are NOT grounds for rejection on their
  own, even if not 100% verifiable; the bar for them is "plausible", not "certain".
  {mode_note}
- If approved, a publish date/time (format YYYY-MM-DDTHH:MM:SS), starting from today. Use your judgement
  to space the approved posts out sensibly across the day(s) so they don't feel clumped together or
  repetitive back-to-back — there are no fixed rules for the time window or minimum spacing, use your
  own sense of what reads naturally for a cinema's audience.

Posts (in order):
{posts_block}

Return exactly one review per post, in the same order they were given.
"""

MOVIE_RELEASE_MODE_NOTE = (
    "Note: this batch is about movies from {cinema_name}'s own confirmed screening lineup (sourced from our "
    "internal release calendar) — their release/screening dates are verified facts, not invented ones. Do NOT "
    "reject a post solely for stating a movie's release or screening date."
)

GENERIC_NEWS_MODE_NOTE = (
    "Note: this batch is general cinema-industry news, not tied to {cinema_name}'s own screening schedule. "
    "Treat any specific movie release/screening date mentioned as an unverifiable claim (we may not actually "
    "screen that title) unless the post clearly frames it as general industry news rather than implying "
    "{cinema_name} is screening it."
)


def _format_posts(posts) -> str:
    blocks = []
    for i, post in enumerate(posts, start=1):
        blocks.append(f"{i}. Title: {post.title}\n   Style: {post.style}\n   Body: {post.body}")
    return "\n\n".join(blocks)


def review_posts(state: GraphState) -> dict:
    posts = state.get("posts", [])
    if not posts:
        return {}

    settings = get_settings()
    mode_note_template = (
        MOVIE_RELEASE_MODE_NOTE if state.get("mode") == "movie_release" else GENERIC_NEWS_MODE_NOTE
    )
    try:
        llm = get_llm("review_posts")
        result = llm.with_structured_output(PostReviews).invoke(
            REVIEW_PROMPT.format(
                cinema_name=settings.cinema_name,
                post_language=settings.post_language,
                today=date.today().isoformat(),
                count=len(posts),
                posts_block=_format_posts(posts),
                mode_note=mode_note_template.format(cinema_name=settings.cinema_name),
            )
        )

        if len(result.reviews) != len(posts):
            logger.warning(
                "Review count mismatch (%d posts vs %d reviews), leaving all unapproved",
                len(posts),
                len(result.reviews),
            )
            return {}

        for post, review in zip(posts, result.reviews):
            post.approved = review.approved
            post.scheduled_at = review.scheduled_at if review.approved else None
            post.rejection_reason = None if review.approved else review.reason
            save_post(post)

        counts = Counter(p.related_movie_title for p in posts if p.approved and p.related_movie_title)
        if counts:
            increment_post_counts(dict(counts))

        return {}
    except Exception:
        logger.warning("Review step failed, leaving all posts unapproved", exc_info=True)
        return {}
