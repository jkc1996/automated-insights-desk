import os

from langchain_openai import ChatOpenAI

from observability.tracing import trace_node
from observability.langfuse_client import langfuse

from router_client.prompts.router_prompt import ROUTER_SUPERVISOR_PROMPT
from router_client.orchestrator.agent_discovery import AgentDiscovery
from router_client.agents.analyst_client import AnalystClient
from router_client.agents.publisher_client import PublisherClient


class RouterOrchestrator:

    def __init__(self, agent_urls):

        self.llm = ChatOpenAI(
            model=os.getenv("DEFAULT_MODEL", "gpt-4o"),
            base_url=os.getenv("PROXY_BASE_URL"),
            api_key=os.getenv("LITELLM_VIRTUAL_KEY")
        )

        self.discovery = AgentDiscovery(agent_urls)
        self.analyst = AnalystClient()
        self.publisher = PublisherClient()

        self.agent_registry = {}

    async def discover_agents(self):
        self.agent_registry = await self.discovery.discover()

    @trace_node("router_supervisor")
    async def supervisor_node(self, state, config, span=None):

        if not self.agent_registry:
            await self.discover_agents()

        user_message = state["messages"][-1].content

        span.update(input=user_message)

        messages = [{"role": "system", "content": ROUTER_SUPERVISOR_PROMPT}] + state["messages"]

        with langfuse.start_as_current_observation(
            name="router_llm_call",
            as_type="generation",
            model=os.getenv("DEFAULT_MODEL", "gpt-4o")
        ) as gen:

            response = await self.llm.ainvoke(messages, config=config)

            gen.update(
                input=str(messages),
                output=response.content
            )

        decision = response.content.lower().strip()

        if "analyze_database" in decision:
            next_step = "analyst"
        elif "publish_report" in decision:
            next_step = "publisher"
        else:
            next_step = "finish"

        span.update(metadata={"decision": next_step})

        return {"next_step": next_step}

    @trace_node("router_call_analyst")
    async def call_analyst(self, state, span=None):
        return await self.analyst.call(state, self.agent_registry)

    @trace_node("router_call_publisher")
    async def call_publisher(self, state, span=None):
        return await self.publisher.call(state, self.agent_registry)