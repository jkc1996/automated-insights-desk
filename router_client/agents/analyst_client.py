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

        timeout = httpx.Timeout(60.0)

        async with httpx.AsyncClient(timeout=timeout) as httpx_client:

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

        # -------- FIXED RESPONSE PARSING --------

        resp_data = response.root

        if hasattr(resp_data, "error") and resp_data.error:
            result_text = f"Analyst Error: {resp_data.error}"

        else:
            task = resp_data.result

            if task and task.status and task.status.message:

                parts = task.status.message.parts

                if parts and hasattr(parts[0], "root"):
                    result_text = parts[0].root.text
                elif parts and hasattr(parts[0], "text"):
                    result_text = parts[0].text
                else:
                    result_text = str(parts)

            else:
                result_text = "No result returned from analyst."

        span.update(output=result_text[:200])

        return {
            "messages": [
                AIMessage(
                    content=f"Analyst Output:\n{result_text}",
                    name="analyst"
                )
            ]
        }