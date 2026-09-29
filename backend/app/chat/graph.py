"""State-based chat assistant: load_actions -> agent -> (tools -> agent)* -> select_action -> reply."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Sequence, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, SystemMessage
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


ACTIONS_PATH = Path(__file__).resolve().parents[3] / "config" / "operator_actions.txt"

SELECT_PROMPT = """
    You write the final reply to a control-room operator.
    You are given a list of candidate operator actions, the conversation, and a draft answer (the last message).
    Pick the single best action for the situation, using only facts from tool results and the draft.
    Keep the draft's key facts, then add "Recommended action: <ID> - <description>" and one sentence on why.
    If the question is not about what to do, or there is not enough data to choose, return the draft
    unchanged without recommending an action. Never invent numbers.
"""


def load_action_text(path: Path = ACTIONS_PATH) -> str:
    """Read the candidate action list, skipping blank and comment lines."""
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return ""
    return "\n".join(line for line in lines if line.strip() and not line.lstrip().startswith("#"))


class ChatState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    selected_target: str | None
    available_actions: str | None


def build_graph(llm: BaseChatModel, tools: Sequence[BaseTool], checkpointer=None, actions_path: Path = ACTIONS_PATH):
    model = llm.bind_tools(list(tools))

    def load_actions(state: ChatState) -> dict:
        """Load the candidate operator actions (plain text for now)."""
        return {"available_actions": load_action_text(actions_path)}

    def agent(state: ChatState) -> dict:
        prompt = SYSTEM_PROMPT
        if state.get("selected_target"):
            prompt += f"\n\nThe operator currently has {state['selected_target']} UTC selected in the UI; 'this time' refers to it."
        if state.get("available_actions"):
            prompt += f"\n\nCandidate operator actions:\n{state['available_actions']}"
        response = model.invoke([SystemMessage(prompt), *state["messages"]])
        return {"messages": [response]}

    def select_action(state: ChatState) -> dict:
        """Pick the best action and write the final reply, replacing the agent's draft."""
        actions = state.get("available_actions")
        if not actions:
            return {}
        draft = state["messages"][-1]
        prompt = f"{SELECT_PROMPT}\n\nCandidate operator actions:\n{actions}"
        response = llm.invoke([SystemMessage(prompt), *state["messages"]])
        return {"messages": [AIMessage(response.content, id=draft.id)]}

    graph = StateGraph(ChatState)
    graph.add_node("load_actions", load_actions)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(list(tools)))
    graph.add_node("select_action", select_action)
    graph.add_edge(START, "load_actions")
    graph.add_edge("load_actions", "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "select_action"})
    graph.add_edge("select_action", END)
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
