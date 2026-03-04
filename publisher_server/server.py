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

from publisher_server.agent import run_publisher

load_dotenv()

class PublisherExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        task_updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        task_updater.submit()
        task_updater.start_work()

        try:
            # --- START OF FIX ---
            first_part = context.message.parts[0]
            
            if hasattr(first_part, "text"):
                raw_input = first_part.text
            elif hasattr(first_part, "root") and hasattr(first_part.root, "text"):
                raw_input = first_part.root.text
            elif isinstance(first_part, dict):
                raw_input = first_part.get("text", str(first_part))
            else:
                raw_input = getattr(first_part, "model_dump", lambda: {"text": str(first_part)})().get("text", str(first_part))
            # --- END OF FIX ---

            # Extract filename from parameters if present, otherwise default
            # Safely extract filename, defaulting if the SDK hides the parameters object
            try:
                filename = context.parameters.get("filename", "q1_growth_analysis.md")
            except AttributeError:
                filename = "q1_growth_analysis.md"
                
            # Execute the LangGraph Publisher
            result = await run_publisher(raw_input, filename)
            final_answer = result["messages"][-1].content

            success_msg = Message(
                messageId=str(uuid.uuid4()),
                role="agent",
                parts=[TextPart(text=final_answer)]
            )
            task_updater.complete(message=success_msg)

        except Exception as e:
            traceback.print_exc()
            error_msg = Message(
                messageId=str(uuid.uuid4()),
                role="agent",
                parts=[TextPart(text=f"Publisher Error: {str(e)}")]
            )
            task_updater.failed(message=error_msg)

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        pass

# Server Metadata
publisher_skills = [
    AgentSkill(
        id="publish_report",
        name="Publish Report",
        description="Saves data to a Markdown report on the filesystem.",
        tags=["filesystem", "markdown"],
        parameters={
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "filename": {"type": "string"}
            },
            "required": ["content"]
        }
    )
]

agent_card = AgentCard(
    name="Forensic Publisher Agent",
    description="Specialist in document persistence.",
    url="http://localhost:8002/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=False),
    skills=publisher_skills
)

request_handler = DefaultRequestHandler(agent_executor=PublisherExecutor(), task_store=InMemoryTaskStore())
a2a_app = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)

if __name__ == "__main__":
    uvicorn.run(a2a_app.build(), host="0.0.0.0", port=8002)