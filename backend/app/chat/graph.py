"""State-based chat assistant: agent -> (tools -> agent)* -> reply."""
from __future__ import annotations

from typing import Annotated, Sequence, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

SYSTEM_PROMPT = """
    You are the Team Blue grid assistant for Ireland's renewable dispatch-down prototype.
    You help operators understand forecasts of national wind and solar dispatch-down.

    Rules:
    - Only state numbers returned by your tools in this conversation. Never estimate or invent figures.
    - If a question needs data, call a tool first. If a tool returns an error, say so plainly.
    - Every forecast here is a historical replay of January 2026 data, not a live forecast. Say so when giving figures.
    - Forecasts are national totals. They do not identify a specific line, wind farm or location.
    - Keep constraint, curtailment and total dispatch-down separate; do not use them interchangeably.
    - Times are UTC. Present probabilities as percentages and energy in MWh with one decimal place.
    - Be concise and write for a control-room operator.
"""


class ChatState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    selected_target: str | None


def build_graph(llm: BaseChatModel, tools: Sequence[BaseTool], checkpointer=None):
    model = llm.bind_tools(list(tools))

    def agent(state: ChatState) -> dict:
        prompt = SYSTEM_PROMPT
        if state.get("selected_target"):
            prompt += f"\n\nThe operator currently has {state['selected_target']} UTC selected in the UI; 'this time' refers to it."
        response = model.invoke([SystemMessage(prompt), *state["messages"]])
        return {"messages": [response]}

    graph = StateGraph(ChatState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(list(tools)))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer or MemorySaver())


def build_azure_llm(settings) -> BaseChatModel:
    from langchain_openai import AzureChatOpenAI

    kwargs = dict(
        azure_endpoint=settings.endpoint,
        api_key=settings.api_key,
        azure_deployment=settings.deployment,
        api_version=settings.api_version,
        max_retries=3,  # the endpoint is shared; back off on 429s
        timeout=60,
    )
    if not settings.is_reasoning_model:
        kwargs["temperature"] = 0
    return AzureChatOpenAI(**kwargs)
