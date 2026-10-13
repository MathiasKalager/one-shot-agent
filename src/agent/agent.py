import asyncio
import json
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from .utils.sanitize_message import sanitize_messages

load_dotenv()

PROMPT = """You are a helpful network AI assistant. 
You get tools from a mcp server.
You are only allowed to use these tools.
the router names are router1, router2, router3. Use this names when you call the tools. (map example: 1 -> router1...) 
When tools are called, report each tool's name and whether its execution succeeded or failed, then give the answer. Do not infer that a router is down from a tool error alone. Be explicit about uncertainty.
Answers should be concise, brief and to the point.
"""

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_input: str

def ingestion(state: AgentState) -> dict:
    user_text = state.get("user_input", "").strip()

    if not user_text:
        return {}

    if not state.get("messages"):
        return {
            "messages": [
                SystemMessage(content=PROMPT),
                HumanMessage(content=user_text),
            ]
        }

    return {
        "messages": [
            HumanMessage(content=user_text)
        ]
    }

def build_graph(llm, tools):
    async def agent(state: AgentState) -> dict:
        try:
            response = await llm.ainvoke(state["messages"])
        except Exception as e:
            if "tool_calls must be followed" in str(e):
                repaired = sanitize_messages(state["messages"])
                response = await llm.ainvoke(repaired)
                return {"messages": [response]}
            raise
        return {"messages": [response]}

    tool_node = ToolNode(tools)
    async def tools_wrapper(state: AgentState):
        try:
            result = await tool_node.ainvoke(state)
        except Exception as e:
            last_msg = state["messages"][-1]
            tool_calls = getattr(last_msg, "tool_calls", None) or []
            tool_responses = []
            for tc in tool_calls:
                tool_responses.append(
                    ToolMessage(
                        tool_call_id=tc["id"],
                        content=json.dumps(
                            {
                                "error": "tool_execution_failed",
                                "tool": tc.get("name"),
                                "message": str(e),
                            }
                        ),
                    )
                )
            return {"messages": tool_responses}

        return result

    graph = StateGraph(AgentState)
    graph.add_node("ingestion", ingestion)
    graph.add_node("llm", agent)
    graph.add_node("tools", tools_wrapper)

    graph.add_edge(START, "ingestion")
    graph.add_edge("ingestion", "llm")

    # Hvis LLM ber om verktøy -> tools, ellers -> END
    graph.add_conditional_edges("llm", tools_condition, {"tools": "tools", "__end__": END})

    # Etter tools-kjøring, tilbake til llm for å fortsette
    graph.add_edge("tools", "llm")

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)

async def main():
    try:
        client = MultiServerMCPClient(
            {
                "AI_MCP_Router": {
                "transport": "streamable_http",
                "url": "http://127.0.0.1:8000/mcp",
                },
            }
        )

        tools = await client.get_tools()

    except Exception as e:
        print(f"Kunne ikke hente tools fra MCP: {e}")
        return

    llm = ChatOpenAI(
        model="gpt-6.1-sol",
        reasoning_effort="medium",
        use_responses_api=True,
        timeout=120,
        max_retries=2,
    ).bind_tools(tools)

    app = build_graph(llm, tools)

    config = {"configurable": {"thread_id": "chat-1"}}

    while True:
        user_text = input("> ").strip()
        if user_text.lower() in {"exit", "quit"}:
            break
        try:
            state = await app.ainvoke({"user_input": user_text}, config=config)
        except Exception as e:
            print(f"Graf-feil: {e}")
            continue

        # Siste AIMessage etter eventuelle tool-runder
        last = state["messages"][-1]
        if isinstance(last, AIMessage):
            print("Assistant:", last.text)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stoppet av bruker")
