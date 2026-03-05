import httpx
import uuid

from langchain_core.messages import AIMessage
from a2a.client import A2AClient
from a2a.types import SendMessageRequest, Message, TextPart

from observability.tracing import trace_node


class PublisherClient:

    @trace_node("publisher_client_request")
    async def call(self, state, agent_registry, span=None):

        report_content = state["messages"][-1].content

        agent_info = agent_registry.get("publish_report")

        if not agent_info:
            return {"messages": [AIMessage(content="Publisher agent not found.", name="publisher")]}

        agent_url = agent_info["agent_url"]
        request_id = str(uuid.uuid4())

        span.update(
            input=report_content[:300],
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
                        parts=[TextPart(text=report_content)]
                    ),
                    "parameters": {
                        "content": report_content,
                        "filename": "reports/q1_growth_analysis.md"
                    }
                }
            )

            response = await client.send_message(request)

        task = response.root.result
        result_text = task.status.message.parts[0].root.text

        span.update(output=result_text)

        return {
            "messages": [
                AIMessage(
                    content=f"Publisher Status:\n{result_text}",
                    name="publisher"
                )
            ]
        }