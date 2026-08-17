from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from social_media_manager_agent.nodes.discovery import (
    discover_generic_news,
    discover_movie_releases,
    route_discovery,
    refine_query
)
from social_media_manager_agent.nodes.selection import select_items
from social_media_manager_agent.state import GraphState
from social_media_manager_agent.nodes.process_item import process_item
from social_media_manager_agent.nodes.review_posts import review_posts
from social_media_manager_agent.config import get_settings


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("discover_generic_news", discover_generic_news)
    graph.add_node("discover_movie_releases", discover_movie_releases)
    graph.add_node("select_items", select_items)

    graph.add_conditional_edges(
        START,
        route_discovery,
        {
            "discover_generic_news": "discover_generic_news",
            "discover_movie_releases": "discover_movie_releases",
        },
    )
    graph.add_edge("discover_generic_news", "select_items")
    graph.add_edge("discover_movie_releases", "select_items")

    graph.add_node("process_item", process_item)
    graph.add_node("review_posts", review_posts)

    graph.add_node("refine_query", refine_query)

    graph.add_conditional_edges("select_items", route_after_selection, ["process_item", "refine_query"])    

    graph.add_conditional_edges(
    "refine_query",
    route_discovery,
    {"discover_generic_news": "discover_generic_news", "discover_movie_releases": "discover_movie_releases"},
)
    graph.add_edge("process_item", "review_posts")
    graph.add_edge("review_posts", END)

    return graph.compile()



def route_after_selection(state: GraphState):
    settings = get_settings()
    if state["selected_items"] or state.get("discovery_attempt", 1) >= settings.max_discovery_attempts:
        return [Send("process_item", {"selected_items": [item]}) for item in state["selected_items"]]
    return "refine_query"