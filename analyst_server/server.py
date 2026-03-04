import uvicorn
import uuid
import traceback
from dotenv import load_dotenv

from a2a.types import AgentCard, AgentCapabilities, AgentSkill, TextPart, Message
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.server.apps import A2AStarletteApplication
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events import EventQueue

from analyst_server.agent import run_analyst

load_dotenv()

# ------------------------------
# 1️⃣ Define the Agent Executor
# ------------------------------
class AnalystExecutor(AgentExecutor):

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        task_updater = TaskUpdater(
            event_queue,
            context.task_id,
            context.context_id
        )

        task_updater.submit()
        task_updater.start_work()

        try:
            # Bulletproof Text Extraction
            first_part = context.message.parts[0]
            
            if hasattr(first_part, "text"):
                user_query = first_part.text
            elif hasattr(first_part, "root") and hasattr(first_part.root, "text"):
                user_query = first_part.root.text
            elif isinstance(first_part, dict):
                user_query = first_part.get("text", str(first_part))
            else:
                user_query = getattr(first_part, "model_dump", lambda: {"text": str(first_part)})().get("text", str(first_part))

            focus_metric = "General Operations"

            # Run the pristine LangGraph Analyst
            result = await run_analyst(user_query, focus_metric)
            final_answer = result["messages"][-1].content

            # Schema-Compliant Success Message
            success_msg = Message(
                messageId=str(uuid.uuid4()),
                role="agent",
                parts=[TextPart(text=final_answer)]
            )
            task_updater.complete(message=success_msg)

        except Exception as e:
            traceback.print_exc()
            
            # Schema-Compliant Error Message
            error_msg = Message(
                messageId=str(uuid.uuid4()),
                role="agent",
                parts=[TextPart(text=f"Analyst Execution Error: {str(e)}")]
            )
            task_updater.failed(message=error_msg)

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        pass


# ------------------------------
# 2️⃣ Define Agent Skills
# ------------------------------
analyst_skills = [
    AgentSkill(
        id="analyze_database",
        name="Analyze Database",
        description="Perform forensic SQL analysis and growth metric calculations.",
        tags=["database", "analytics", "sql"],
        parameters={
            "type": "object",
            "properties": {
                "user_query": {
                    "type": "string",
                    "description": "Natural language question from the user"
                }
            },
            "required": ["user_query"]
        }
    )
]

# ------------------------------
# 3️⃣ Define Agent Card
# ------------------------------
agent_card = AgentCard(
    name="Forensic Analyst Agent",
    description="A specialist in SQL extraction and advanced growth metrics using MCP tools.",
    url="http://localhost:8001/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=False),
    skills=analyst_skills
)

# ------------------------------
# 4️⃣ Boilerplate Startup
# ------------------------------
executor = AnalystExecutor()
request_handler = DefaultRequestHandler(
    agent_executor=executor,
    task_store=InMemoryTaskStore()
)

a2a_app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
)

if __name__ == "__main__":
    print("🚀 Analyst A2A Server running at http://localhost:8001")
    uvicorn.run(
        a2a_app.build(),
        host="0.0.0.0",
        port=8001
    )