from langchain_tavily import TavilySearch
from social_media_manager_agent.config import get_settings
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _search(query: str, max_results: int, *, topic: str = "general", time_range: str | None = None) -> list[dict]:
    settings = get_settings()
    tool = TavilySearch(
        max_results=max_results,
        tavily_api_key=settings.tavily_api_key,
        topic=topic,
        time_range=time_range,
    )
    response = tool.invoke({"query": query[:400]})
    return response["results"]

def broad_search(query: str, max_results: int = 8, *, time_range: str | None = None) -> list[dict]:
    """Broad search — replaces the ADK `scouter`/`movie_scouter`."""
    return _search(query, max_results, topic="news", time_range=time_range)

def focused_search(query: str, max_results: int = 4, *, time_range: str | None = None) -> list[dict]:
    """Focused in-depth search — replaces the entire `grounder_specifico` sub-agent."""
    return _search(query, max_results, topic="general", time_range=time_range)

def format_results(results: list[dict]) -> str:
    return "\n\n".join(f"- {r['title']}\n  {r.get('content', '')}" for r in results)