import os

from langchain_openai import ChatOpenAI

from social_media_manager_agent.config import get_settings


def get_llm(node_name: str | None = None, temperature: float = 0) -> ChatOpenAI:
    settings = get_settings()

    model = settings.default_model
    if node_name:
        override = os.getenv(f"MODEL_{node_name.upper()}")
        if override:
            model = override

    return ChatOpenAI(model=model, temperature=temperature, api_key=settings.openai_api_key)