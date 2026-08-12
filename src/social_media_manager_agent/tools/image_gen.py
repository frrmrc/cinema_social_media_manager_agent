import base64
import logging

from openai import BadRequestError, OpenAI

from social_media_manager_agent.config import get_settings
from social_media_manager_agent.schemas import Post

logger = logging.getLogger(__name__)

IMAGE_PROMPT = """Generate a social media image for a cinema, following the layout of the attached brand identity template (the font, color palette, and visual tone must remain consistent). If you consider it necessary, you may use the icons and graphics included in the template.

Include a short, engaging text in the image (maximum one sentence, poster-style) inspired by this post:
Title: {title}
Style: {style}
Content: {body}

You have creative freedom when designing the image: you can add new and content-related icons, graphics, illustrations, and shapes inspired by the brand identity and consistent with it.
"""

IMAGE_PROMPT_FALLBACK = """Generate a simple, safe social media image for a cinema, following the layout of the attached brand identity template (font, color palette, visual tone consistent with the template).

Keep the image minimal and tasteful: use only the brand template's graphic elements (icons, shapes, colors) plus the following title as short text overlay. Avoid depicting people, violence, weapons, or any sensitive imagery.

Title: {title}
"""


def _edit_image(client: OpenAI, settings, prompt: str) -> bytes:
    with open(settings.brand_template_path, "rb") as template_file:
        result = client.images.edit(
            model=settings.image_model,
            image=[template_file],
            prompt=prompt,
            size=settings.image_size,
            quality=settings.image_quality,
            n=1,
        )
    return base64.b64decode(result.data[0].b64_json)


def generate_image_bytes(post: Post) -> bytes | None:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    primary_prompt = IMAGE_PROMPT.format(title=post.title, style=post.style, body=post.body)
    try:
        return _edit_image(client, settings, primary_prompt)
    except BadRequestError as exc:
        if exc.code != "moderation_blocked":
            raise
        logger.warning("Image blocked by moderation for '%s', retrying with a sanitized prompt", post.title)

    fallback_prompt = IMAGE_PROMPT_FALLBACK.format(title=post.title)
    try:
        return _edit_image(client, settings, fallback_prompt)
    except BadRequestError as exc:
        if exc.code != "moderation_blocked":
            raise
        logger.warning("Sanitized image also blocked for '%s', continuing without image", post.title)
        return None