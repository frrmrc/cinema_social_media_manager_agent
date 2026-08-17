import logging

from social_media_manager_agent.config import get_settings
from social_media_manager_agent.models import get_llm
from social_media_manager_agent.schemas import PostReviews
from social_media_manager_agent.state import GraphState
from social_media_manager_agent.tools.storage import save_post
from datetime import date

logger = logging.getLogger(__name__)


REVIEW_PROMPT = """You are the final reviewer for {cinema_name}'s Instagram account, scheduling today's
batch of {count} generated posts. Today is {today}.

For each post, decide:
- Whether it is ready to be published as-is, with no further human review. Approve it ONLY if ALL of the
  following hold: the caption is complete, coherent {post_language} text with no placeholder text (e.g.
  "[Cinema Name]", "TBD", "lorem ipsum"); it does not present invented, unverifiable specific facts (exact
  prices, exact showtimes, direct quotes) as certain; the tone and content are appropriate for a public
  brand account; and it is clearly on-topic for a cinema's social media presence.
- If approved, a publish date/time (format YYYY-MM-DDTHH:MM:SS), starting from today. Use your judgement
  to space the approved posts out sensibly across the day(s) so they don't feel clumped together or
  repetitive back-to-back — there are no fixed rules for the time window or minimum spacing, use your
  own sense of what reads naturally for a cinema's audience.

Posts (in order):
{posts_block}

Return exactly one review per post, in the same order they were given.
"""


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
    try:
        llm = get_llm("review_posts")
        result = llm.with_structured_output(PostReviews).invoke(
            REVIEW_PROMPT.format(
                cinema_name=settings.cinema_name,
                post_language=settings.post_language,
                today=date.today().isoformat(),
                count=len(posts),
                posts_block=_format_posts(posts),
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

        return {}
    except Exception:
        logger.warning("Review step failed, leaving all posts unapproved", exc_info=True)
        return {}
