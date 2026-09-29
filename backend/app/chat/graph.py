"""State-based chat assistant: agent -> (tools -> agent)* -> reply."""

from __future__ import annotations

import time
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
    You help operators understand forecasts and the evidence-gated advisory decision flow.

    Rules:
    - Only state numbers returned by your tools in this conversation. Never estimate or invent figures.
    - If a question needs data, call a tool first. If a tool returns an error, say so plainly.
    - Choose tools by target and time: January dispatch-down and saved constraint tools are historical replays; current GFS tools are checked experimental forward national constraint forecasts. Never describe one as the other.
    - A missing or expired current forecast is unavailable, not zero. Never substitute a historical replay for a future question.
    - When using the experimental GFS forecast, disclose the limitations listed in the tool result.
    - National results do not identify a specific line, wind farm or location. The separate network tool is an input-gated TYTFS planning-case DC scenario, not live topology, a security verdict, or avoided-energy proof.
    - Keep constraint, curtailment and total dispatch-down separate; do not use them interchangeably.
    - The locked scenario IDs are T1-T4, H1-H4 and SNSP. Before proposing any operator action, call get_scenario_actions with the scenario IDs established by the case. Do not invent an action outside that tool's result.
    - An action returned by get_scenario_actions is only in scope. It is not safe or available merely because it is eligible. Recommend an exact action only when tool results provide the required action inputs plus reviewed network and safety evidence for that exact action. Otherwise explain the blockers.
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
        max_retries=3,
        timeout=60,
    )
    if not settings.is_reasoning_model:
        kwargs["temperature"] = 0
    return AzureChatOpenAI(**kwargs)


def _step_detail(node: str, update: dict) -> str:
    messages = update.get("messages") or []
    if node == "agent":
        calls = [call["name"] for m in messages for call in (getattr(m, "tool_calls", None) or [])]
        return f"requested {', '.join(calls)}" if calls else "drafted an answer"
    if node == "tools":
        names = [m.name for m in messages if getattr(m, "name", None)]
        return f"ran {', '.join(names)}" if names else "ran tools"
    return ""


def _step_tools(node: str, update: dict) -> list[dict]:
    """Per-tool detail for a step: what the agent asked for, or how each tool came back."""
    messages = update.get("messages") or []
    if node == "agent":
        return [{"name": c["name"], "args": c.get("args") or {}} for m in messages for c in (getattr(m, "tool_calls", None) or [])]
    if node == "tools":
        out = []
        for m in messages:
            if not getattr(m, "name", None):
                continue
            text = str(m.content)
            out.append({"name": m.name, "ok": getattr(m, "status", "success") != "error" and '"error"' not in text[:200]})
        return out
    return []


def run_with_trace(graph, inputs: dict, config: dict) -> tuple[dict, list[dict]]:
    """Run one turn and record every node that actually executed, in order.

    The compiled graph has conditional edges (agent -> tools or select_action),
    so the path differs per question. Streaming node updates gives the real
    path: START, then each node as it ran, then END. Updates arrive as each
    node finishes, so the gap between them is that node's run time.
    """
    trace = [{"node": "__start__", "detail": "", "duration_ms": 0, "tools": []}]
    last = time.perf_counter()
    for chunk in graph.stream(inputs, config, stream_mode="updates"):
        now = time.perf_counter()
        for node, update in chunk.items():
            update = update or {}
            trace.append({"node": node, "detail": _step_detail(node, update),
                          "duration_ms": round((now - last) * 1000), "tools": _step_tools(node, update)})
        last = now
    trace.append({"node": "__end__", "detail": "", "duration_ms": 0, "tools": []})
    return graph.get_state(config).values, trace
