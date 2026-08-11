from langchain_tavily import TavilySearch

from social_media_manager_agent.config import get_settings


def _search(query: str, max_results: int) -> list[dict]:
    settings = get_settings()
    tool = TavilySearch(max_results=max_results, tavily_api_key=settings.tavily_api_key)
    response = tool.invoke({"query": query})
    return response["results"]

def broad_search(query: str, max_results: int = 8) -> list[dict]:
    """Ricerca ampia — sostituisce lo `scouter`/`movie_scouter` di ADK."""
    return _search(query, max_results)

def focused_search(query: str, max_results: int = 4) -> list[dict]:
    """Ricerca mirata di approfondimento — sostituisce l'intero sub-agente `grounder_specifico`."""
    return _search(query, max_results)

def format_results(results: list[dict]) -> str:
    return "\n\n".join(f"- {r['title']}\n  {r.get('content', '')}" for r in results)