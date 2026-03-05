from langgraph.graph import StateGraph, START, END
from router_client.orchestrator.state import RouterState


def build_graph(orchestrator):

    builder = StateGraph(RouterState)

    builder.add_node("supervisor", orchestrator.supervisor_node)
    builder.add_node("analyst", orchestrator.call_analyst)
    builder.add_node("publisher", orchestrator.call_publisher)

    builder.add_edge(START, "supervisor")

    builder.add_conditional_edges(
        "supervisor",
        lambda x: x["next_step"],
        {
            "analyst": "analyst",
            "publisher": "publisher",
            "finish": END
        }
    )

    builder.add_edge("analyst", "supervisor")
    builder.add_edge("publisher", "supervisor")

    return builder