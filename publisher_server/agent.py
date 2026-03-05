import os
import json
from typing import Annotated, TypedDict

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

from observability.tracing import trace_node

load_dotenv()


class PublisherState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class PublisherGraphBuilder:

    def __init__(self):

        self.llm = ChatOpenAI(
            model=os.getenv("DEFAULT_MODEL", "gpt-4o"),
            base_url=os.getenv("PROXY_BASE_URL"),
            api_key=os.getenv("LITELLM_VIRTUAL_KEY")
        )

    @trace_node("publisher_reasoning")
    async def call_publisher_model(self, state: PublisherState, config, span=None):

        system_prompt = (
            "You are the Forensic Publisher Agent.\n"
            "Save the provided report using the write_file tool."
        )

        tools = config["configurable"]["formatted_tools"]

        content = state["messages"][-1].content

        span.update(
            input=content,
            metadata={
                "node": "publisher_reasoning",
                "tools_available": len(tools)
            }
        )

        llm_with_tools = self.llm.bind_tools(tools)

        messages = [{"role": "system", "content": system_prompt}] + state["messages"]

        response = await llm_with_tools.ainvoke(messages)

        span.update(metadata={"tool_call": True})

        return {"messages": [response]}

    @trace_node("publisher_tool_execution")
    async def execute_filesystem_tools(self, state: PublisherState, config, span=None):

        last_msg = state["messages"][-1]

        session: ClientSession = config["configurable"]["mcp_session"]

        outputs = []

        tool_calls = getattr(last_msg, "tool_calls", None) or []

        for call in tool_calls:

            tool_name = call["name"]

            try:

                result = await session.call_tool(
                    name=tool_name,
                    arguments=call["args"]
                )

                text = result.content[0].text if result.content else "File saved."

            except Exception as e:
                text = f"Filesystem error: {str(e)}"

            span.update(
                metadata={
                    "tool": tool_name,
                    "result_preview": text[:200]
                }
            )

            outputs.append(
                ToolMessage(
                    content=text,
                    tool_call_id=call["id"]
                )
            )

        return {"messages": outputs}

    def should_continue(self, state: PublisherState):

        last_msg = state["messages"][-1]

        if getattr(last_msg, "tool_calls", None):
            return "execute_tools"

        return END

    def build(self):

        workflow = StateGraph(PublisherState)

        workflow.add_node("publisher", self.call_publisher_model)
        workflow.add_node("execute_tools", self.execute_filesystem_tools)

        workflow.add_edge(START, "publisher")

        workflow.add_conditional_edges(
            "publisher",
            self.should_continue
        )

        workflow.add_edge("execute_tools", "publisher")

        return workflow.compile()


async def run_publisher(report_content: str, filename: str):

    with open("mcp_servers.json", "r") as f:
        mcp_config = json.load(f)["mcpServers"]

    fs_params = StdioServerParameters(
        command=mcp_config["filesystem_server"]["command"],
        args=mcp_config["filesystem_server"]["args"]
    )

    async with stdio_client(fs_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            tools = await session.list_tools()

            formatted_tools = [{
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema
                }
            } for t in tools.tools]

            builder = PublisherGraphBuilder()
            graph = builder.build()

            config = {
                "configurable": {
                    "mcp_session": session,
                    "formatted_tools": formatted_tools
                }
            }

            prompt = f"Save this report as '{filename}':\n\n{report_content}"

            return await graph.ainvoke(
                {"messages": [("user", prompt)]},
                config=config
            )