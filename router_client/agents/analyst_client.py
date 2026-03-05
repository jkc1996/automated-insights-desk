import httpx
import uuid

from langchain_core.messages import AIMessage
from a2a.client import A2AClient
from a2a.types import SendMessageRequest, Message, TextPart

from observability.tracing import trace_node


class AnalystClient:

    @trace_node("analyst_client_request")
    async def call(self, state, agent_registry, span=None):

        user_query = next(
            m.content for m in reversed(state["messages"])
            if getattr(m, "type", None) == "human"
        )

        agent_info = agent_registry.get("analyze_database")

        if not agent_info:
            return {"messages": [AIMessage(content="Analyst agent not found.", name="analyst")]}

        agent_url = agent_info["agent_url"]

        request_id = str(uuid.uuid4())

        span.update(
            input=user_query,
            metadata={
                "agent_url": agent_url,
                "request_id": request_id
            }
        )

        async with httpx.AsyncClient(timeout=60.0) as httpx_client:

            client = A2AClient(httpx_client=httpx_client, url=agent_url)

            request = SendMessageRequest(
                params={
                    "message": Message(
                        messageId=request_id,
                        role="user",
                        parts=[TextPart(text=user_query)]
                    ),
                    "parameters": {"user_query": user_query}
                }
            )

            response = await client.send_message(request)

        task = response.root.result
        result_text = task.status.message.parts[0].root.text

        span.update(output=result_text)

        return {
            "messages": [
                AIMessage(
                    content=f"Analyst Output:\n{result_text}",
                    name="analyst"
                )
            ]
        }