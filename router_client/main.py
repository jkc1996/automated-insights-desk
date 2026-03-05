import os
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.redis import AsyncRedisSaver

from guardrails.intent_guardrail import check_user_intent

from router_client.orchestrator.router_orchestrator import RouterOrchestrator
from router_client.orchestrator.graph_builder import build_graph

from observability.tracing import trace_node

from langfuse.langchain import CallbackHandler

load_dotenv()

AGENT_URLS = [
    "http://localhost:8001",
    "http://localhost:8002"
]


@trace_node("user_question", as_type="generation")
async def process_chat(user_input: str, thread_id: str, span=None):

    span.update(
        input=user_input,
        metadata={"component": "router_entry"}
    )

    orchestrator = RouterOrchestrator(AGENT_URLS)

    allowed, guardrail_message = await check_user_intent(
        orchestrator.llm,
        user_input
    )

    if not allowed:
        span.update(metadata={"blocked_by_guardrail": True})
        return guardrail_message

    await orchestrator.discover_agents()

    async with AsyncRedisSaver.from_conn_string("redis://localhost:6379") as memory:

        builder = build_graph(orchestrator)
        graph = builder.compile(checkpointer=memory)

        handler = CallbackHandler()

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [handler]
        }

        agent_outputs = []

        async for event in graph.astream(
            {"messages": [HumanMessage(content=user_input)]},
            config,
            stream_mode="values"
        ):

            last_msg = event["messages"][-1].content

            if "Analyst Output:" in last_msg or "Publisher Status:" in last_msg:

                if last_msg not in agent_outputs:
                    agent_outputs.append(last_msg)

        if agent_outputs:

            final_output = "\n\n---\n\n".join(agent_outputs)

            span.update(output=final_output)

            return final_output

        span.update(metadata={"no_agent_output": True})

        return "No agent output was generated."