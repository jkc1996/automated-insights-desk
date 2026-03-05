import httpx

from observability.tracing import trace_node
from observability.langfuse_client import langfuse


class AgentDiscovery:

    def __init__(self, agent_urls):
        self.agent_urls = agent_urls
        self.registry = {}

    @trace_node("agent_discovery")
    async def discover(self, span=None):

        registry = {}

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:

            for url in self.agent_urls:

                try:
                    resp = await client.get(f"{url}/.well-known/agent.json")
                    agent_card = resp.json()

                    for skill in agent_card.get("skills", []):

                        skill_id = skill["id"]

                        registry[skill_id] = {
                            "agent_url": url,
                            "name": agent_card.get("name"),
                            "description": skill.get("description")
                        }

                except Exception as e:

                    langfuse.update_current_observation(
                        metadata={
                            "agent_url": url,
                            "discovery_error": str(e)
                        }
                    )

                    print(f"Discovery failed for {url}: {e}")

        self.registry = registry

        return registry