import base64

from openai import OpenAI

from social_media_manager_agent.config import get_settings
from social_media_manager_agent.schemas import Post

IMAGE_PROMPT = """Genera un'immagine social per un cinema, seguendo il layout del template di brand identity allegato (font, palette e tono visivo devono restare coerenti). Se lo ritieni necessario puoi servirti delle icone e grafiche presenti.

Includi nell'immagine un testo breve e accattivante (massimo una frase, stile locandina) ispirato a questo post:
Titolo: {title}
Stile: {style}
Contenuto: {body}

libertà di inferenza nella creazione dell'immagine: l'immagine può contenere icone, grafiche, disegni, forme ispirate alla brand identity e coerenti con questa.
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