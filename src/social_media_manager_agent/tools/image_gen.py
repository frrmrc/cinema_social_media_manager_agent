import base64

from openai import OpenAI

from social_media_manager_agent.config import get_settings
from social_media_manager_agent.schemas import Post

IMAGE_PROMPT = """Generate a social media image for a cinema, following the layout of the attached brand identity template (font, palette and visual tone must remain consistent). If you deem it necessary, you may make use of the icons and graphics present.

Include in the image a short, eye-catching text (at most one sentence, poster style) inspired by this post:
Title: {title}
Style: {style}
Content: {body}

Feel free to use inference when creating the image: it may contain icons, graphics, drawings, shapes inspired by and consistent with the brand identity.
"""

def generate_image_bytes(post: Post) -> bytes:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    with open(settings.brand_template_path, "rb") as template_file:
        result = client.images.edit(
            model=settings.image_model,
            image=[template_file],
            prompt=IMAGE_PROMPT.format(title=post.title, style=post.style, body=post.body),
            size=settings.image_size,
            quality=settings.image_quality,
            n=1,
            moderation = 'low'

        )
        

    return base64.b64decode(result.data[0].b64_json)