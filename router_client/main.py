import os
import httpx
import uuid
from typing import Annotated, TypedDict

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from a2a.client import A2AClient
from a2a.types import SendMessageRequest, Message, TextPart

from langgraph.checkpoint.redis import AsyncRedisSaver

from langfuse.langchain import CallbackHandler
from observability.tracing import trace_node
from guardrails.intent_guardrail import check_user_intent

load_dotenv()

AGENT_URLS = [
    "http://localhost:8001",
    "http://localhost:8002"
]

langfuse_handler = CallbackHandler()


class RouterState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next_step: str


class RouterOrchestrator:

    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("DEFAULT_MODEL", "gpt-4o"),
            base_url=os.getenv("PROXY_BASE_URL"),
            api_key=os.getenv("LITELLM_VIRTUAL_KEY")
        )
        self.agent_registry = {}

    async def discover_agents(self):

        registry = {}

        async with httpx.AsyncClient() as client:

            for url in AGENT_URLS:

                try:
                    resp = await client.get(f"{url}/.well-known/agent.json")
                    agent_card = resp.json()

                    for skill in agent_card.get("skills", []):
                        skill_id = skill["id"]

                        registry[skill_id] = {
                            "agent_url": url,
                            "name": agent_card["name"],
                            "description": skill["description"]
                        }

                except Exception as e:
                    print(f"Discovery failed for {url}: {e}")

        self.agent_registry = registry

    @trace_node("router_supervisor")
    async def supervisor_node(self, state: RouterState, config):

        if not self.agent_registry:
            await self.discover_agents()

        system_prompt = """
        You are the Supervisor of a multi-agent analytics system.

        Your responsibility is to decide which agent should act next.

        --------------------------------------------------
        AVAILABLE AGENTS
        --------------------------------------------------

        analyze_database
        → Executes SQL queries and performs data analysis.

        publish_report
        → Saves reports or creates files in the filesystem.

        --------------------------------------------------
        CONVERSATION STRUCTURE
        --------------------------------------------------

        The conversation may contain messages from:

        User
        Analyst Output
        Publisher Status

        These messages indicate the current stage of the workflow.

        --------------------------------------------------
        DECISION LOGIC
        --------------------------------------------------

        Follow these rules strictly:

        1. If the conversation contains a message starting with:

        Publisher Status

        → The file/report has already been saved.
        → The workflow is complete.

        Return:
        finish


        2. If the latest user request is about creating, saving, or writing a file
        (for example: "create a markdown file", "save a report", "write a file", 
        "create a file in the reports folder")

        AND there is NO Publisher Status yet

        → The task should be handled by the Publisher agent.

        Return:
        publish_report


        3. If the conversation contains:

        Analyst Output

        AND there is NO Publisher Status yet

        → The analyst has completed the analysis.
        → The result should now be saved by the Publisher.

        Return:
        publish_report


        4. If the conversation does NOT contain:

        Analyst Output

        → The analysis has not yet been performed.

        Return:
        analyze_database


        --------------------------------------------------
        CRITICAL RULES
        --------------------------------------------------

        • The analyst must never be called more than once for the same request.
        • The publisher should only run once per request.
        • Only one agent acts at a time.
        • Once a Publisher Status message exists, the workflow must end.

        Typical workflow:

        Analytics request:
        User → Analyst → Publisher → Finish

        File creation request:
        User → Publisher → Finish

        --------------------------------------------------
        OUTPUT FORMAT (STRICT)

        Return ONLY one of these words:

        analyze_database
        publish_report
        finish

        Do NOT include explanations.
        Do NOT include punctuation.
        Return ONLY the command.
        """

        messages = [{"role": "system", "content": system_prompt}] + state["messages"]

        response = await self.llm.ainvoke(messages, config=config)

        decision = response.content.lower().strip()

        if "analyze_database" in decision:
            next_step = "analyst"
        elif "publish_report" in decision:
            next_step = "publisher"
        else:
            next_step = "finish"

        return {"next_step": next_step}

    def _extract_text_safely(self, part):

        if hasattr(part, "text"):
            return part.text

        elif hasattr(part, "root") and hasattr(part.root, "text"):
            return part.root.text

        elif isinstance(part, dict):
            return part.get("text", str(part))

        else:
            return getattr(part, "model_dump", lambda: {"text": str(part)})().get("text", str(part))

    @trace_node("router_call_analyst")
    async def call_analyst(self, state: RouterState):

        user_query = next(
            m.content for m in reversed(state["messages"])
            if getattr(m, "type", None) == "human"
        )

        agent_info = self.agent_registry.get("analyze_database")

        if not agent_info:
            return {"messages": [AIMessage(content="Analyst agent not found.", name="analyst")]}

        agent_url = agent_info["agent_url"]

        timeout = httpx.Timeout(60.0)

        async with httpx.AsyncClient(timeout=timeout) as httpx_client:

            client = A2AClient(httpx_client=httpx_client, url=agent_url)

            request = SendMessageRequest(
                params={
                    "message": Message(
                        messageId=str(uuid.uuid4()),
                        role="user",
                        parts=[TextPart(text=user_query)]
                    ),
                    "parameters": {"user_query": user_query}
                }
            )

            response = await client.send_message(request)

        resp_data = response.root

        if hasattr(resp_data, "error") and resp_data.error:
            result_text = f"Analyst Error: {resp_data.error}"

        else:

            actual_result = resp_data.result

            if hasattr(actual_result, "status") and hasattr(actual_result.status, "message"):
                result_text = self._extract_text_safely(actual_result.status.message.parts[0])
            else:
                result_text = str(actual_result)

        return {
            "messages": [
                AIMessage(content=f"Analyst Output:\n{result_text}", name="analyst")
            ]
        }

    @trace_node("router_call_publisher")
    async def call_publisher(self, state: RouterState):

        report_content = state["messages"][-1].content

        agent_info = self.agent_registry.get("publish_report")

        if not agent_info:
            return {"messages": [AIMessage(content="Publisher agent not found.", name="publisher")]}

        agent_url = agent_info["agent_url"]

        timeout = httpx.Timeout(60.0)

        async with httpx.AsyncClient(timeout=timeout) as httpx_client:

            client = A2AClient(httpx_client=httpx_client, url=agent_url)

            request = SendMessageRequest(
                params={
                    "message": Message(
                        messageId=str(uuid.uuid4()),
                        role="user",
                        parts=[TextPart(text=report_content)]
                    ),
                    "parameters": {
                        "content": report_content,
                        "filename": "q1_growth_analysis.md"
                    }
                }
            )

            response = await client.send_message(request)

        resp_data = response.root

        if hasattr(resp_data, "error") and resp_data.error:
            result_text = f"Publisher Error: {resp_data.error}"

        else:

            actual_result = resp_data.result

            if hasattr(actual_result, "status") and hasattr(actual_result.status, "message"):
                result_text = self._extract_text_safely(actual_result.status.message.parts[0])
            else:
                result_text = str(actual_result)

        return {
            "messages": [
                AIMessage(content=f"Publisher Status:\n{result_text}", name="publisher")
            ]
        }

    def build_graph(self):

        builder = StateGraph(RouterState)

        builder.add_node("supervisor", self.supervisor_node)
        builder.add_node("analyst", self.call_analyst)
        builder.add_node("publisher", self.call_publisher)

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


async def process_chat(user_input: str, thread_id: str):

    orchestrator = RouterOrchestrator()

    # -------- GUARDRAIL CHECK --------
    allowed, guardrail_message = await check_user_intent(
        orchestrator.llm,
        user_input
    )

    if not allowed:
        return guardrail_message
    # ---------------------------------

    await orchestrator.discover_agents()

    async with AsyncRedisSaver.from_conn_string("redis://localhost:6379") as memory:

        builder = orchestrator.build_graph()

        graph = builder.compile(checkpointer=memory)

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [langfuse_handler]
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
            return "\n\n---\n\n".join(agent_outputs)

        return "No agent output was generated."