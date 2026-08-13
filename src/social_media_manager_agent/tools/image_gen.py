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
Language: {post_language}

You have creative freedom when designing the image: you can add new and content-related icons, graphics, illustrations, and shapes inspired by the brand identity and consistent with it.
Prefer graphics, illustrations, shapes over text walls.
"""

IMAGE_PROMPT_FALLBACK = """
Generate a social media image for a cinema using the attached brand identity template as the primary visual reference. Preserve the template’s overall visual language, including typography, color palette, composition style, and tone. You may reuse simple icons, shapes, or graphic elements from the template when appropriate.

Create a clean, original, cinema-related visual inspired by the following social media post:

Title: {title}
Style: {style}
Content: {body}
Language: {post_language}

Include one short, engaging poster-style sentence in {post_language}, with a maximum of one sentence. Keep the text concise and visually secondary to the main graphic.

Use creative freedom to develop the visual: add simple cinema-related illustrations, icons, abstract shapes, or decorative elements that fit the brand identity. Prioritize visual communication over large amounts of text.

Avoid depicting identifiable real people, graphic violence, sexual content, illegal activities, or other potentially sensitive imagery. If the subject matter could be visually sensitive, represent it through neutral cinematic symbolism, abstract graphics, objects, environments, or typography instead.

The final image should feel like an authentic branded cinema social media post, polished, contemporary, and visually coherent with the supplied template.


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

    primary_prompt = IMAGE_PROMPT.format(title=post.title, style=post.style, body=post.body, post_language=settings.post_language)
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