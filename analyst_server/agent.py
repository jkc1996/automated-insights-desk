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


class AnalystState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class AnalystGraphBuilder:

    def __init__(self):

        self.llm = ChatOpenAI(
            model=os.getenv("DEFAULT_MODEL", "gpt-4.1"),
            base_url=os.getenv("PROXY_BASE_URL"),
            api_key=os.getenv("LITELLM_VIRTUAL_KEY"),
            temperature=0
        )

    # ---------------- LLM NODE ----------------

    @trace_node("analyst_reasoning")
    async def call_model(self, state: AnalystState, config, span=None):

        system_prompt = config["configurable"]["system_prompt"]
        tools = config["configurable"]["formatted_tools"]

        user_query = state["messages"][-1].content

        span.update(
            input=user_query,
            metadata={
                "node": "analyst_reasoning",
                "tools_available": len(tools)
            }
        )

        llm_with_tools = self.llm.bind_tools(tools)

        messages = [{"role": "system", "content": system_prompt}] + state["messages"]

        response = await llm_with_tools.ainvoke(messages)

        span.update(
            metadata={
                "tool_calls_detected": bool(getattr(response, "tool_calls", None))
            }
        )

        return {"messages": [response]}

    # ---------------- TOOL EXECUTION ----------------

    @trace_node("analyst_tool_execution")
    async def execute_tools(self, state: AnalystState, config, span=None):

        last_msg = state["messages"][-1]
        tool_map = config["configurable"]["tool_map"]

        outputs = []

        tool_calls = getattr(last_msg, "tool_calls", None) or []

        span.update(metadata={"tool_calls": len(tool_calls)})

        for call in tool_calls:

            tool_name = call["name"]

            span.update(metadata={"tool": tool_name})

            try:

                session: ClientSession = tool_map.get(tool_name)

                result = await session.call_tool(
                    name=tool_name,
                    arguments=call["args"]
                )

                if result.content:
                    text = result.content[0].text
                else:
                    text = "Tool returned no output."

            except Exception as e:
                text = f"Tool error: {str(e)}"

            if tool_name == "read_query":

                sql_query = call["args"].get("query", "")

                span.update(
                    metadata={
                        "sql_query": sql_query,
                        "sql_result_preview": text[:200]
                    }
                )

                debug_text = f"""
SQL Executed:
{sql_query}

Result:
{text}
"""

                outputs.append(
                    ToolMessage(
                        content=debug_text,
                        tool_call_id=call["id"]
                    )
                )

            else:

                span.update(metadata={"tool_result_preview": text[:200]})

                outputs.append(
                    ToolMessage(
                        content=text,
                        tool_call_id=call["id"]
                    )
                )

        return {"messages": outputs}

    # ---------------- ROUTING ----------------

    def should_continue(self, state: AnalystState):

        last_msg = state["messages"][-1]

        if getattr(last_msg, "tool_calls", None):
            return "execute_tools"

        return END

    # ---------------- GRAPH ----------------

    def build(self):

        workflow = StateGraph(AnalystState)

        workflow.add_node("agent", self.call_model)
        workflow.add_node("execute_tools", self.execute_tools)

        workflow.add_edge(START, "agent")

        workflow.add_conditional_edges(
            "agent",
            self.should_continue
        )

        workflow.add_edge("execute_tools", "agent")

        return workflow.compile()


# ---------------- ORCHESTRATOR ----------------


async def run_analyst(user_input: str, focus_metric: str):

    with open("mcp_servers.json", "r") as f:
        mcp_config = json.load(f)["mcpServers"]

    sqlite_params = StdioServerParameters(
        command=mcp_config["sqlite_server"]["command"],
        args=mcp_config["sqlite_server"]["args"]
    )

    custom_params = StdioServerParameters(
        command=mcp_config["custom_analytics"]["command"],
        args=mcp_config["custom_analytics"]["args"]
    )

    async with stdio_client(custom_params) as (c_read, c_write), \
               stdio_client(sqlite_params) as (s_read, s_write):

        async with ClientSession(c_read, c_write) as custom_session, \
                   ClientSession(s_read, s_write) as sqlite_session:

            await custom_session.initialize()
            await sqlite_session.initialize()

            prompt_data = await custom_session.get_prompt(
                name="forensic_analysis_prompt",
                arguments={"focus_metric": focus_metric}
            )

            sys_prompt = prompt_data.messages[0].content.text

            sqlite_tools = await sqlite_session.list_tools()
            custom_tools = await custom_session.list_tools()

            formatted_tools = []
            tool_map = {}

            for t in sqlite_tools.tools:

                tool_map[t.name] = sqlite_session

                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema
                    }
                })

            for t in custom_tools.tools:

                tool_map[t.name] = custom_session

                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema
                    }
                })

            builder = AnalystGraphBuilder()
            graph = builder.build()

            config = {
                "configurable": {
                    "system_prompt": sys_prompt,
                    "tool_map": tool_map,
                    "formatted_tools": formatted_tools
                }
            }

            inputs = {"messages": [("user", user_input)]}

            return await graph.ainvoke(inputs, config=config)