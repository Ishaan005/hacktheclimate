"""Chat pipeline: START -> run_all_tools -> answer -> END.

Every tool runs on every question, in code, in parallel. A tool that does not
fit the question (e.g. a January replay for a September time) returns
{"status": "not_applicable", ...} instead of data. The model is then called
once, with no tools bound, to write the reply from those results.
"""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Sequence, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
    You are the Team Blue grid assistant for Ireland's renewable dispatch-down prototype.
    You help operators understand forecasts and the evidence-gated advisory decision flow.

    Every tool has already been run for this question; the results are below.
    Rules:
    - Only state numbers that appear in the tool results. Never estimate or invent figures.
    - Ignore any result with status "not_applicable" and do not mention it. If a result has an "error", say so plainly only when it is relevant to the question.
    - January dispatch-down and constraint results are historical replays; current GFS results are checked experimental forward national constraint forecasts. Never describe one as the other.
    - A missing or expired current forecast is unavailable, not zero. Never substitute a historical replay for a future question.
    - When using the experimental GFS forecast, disclose the limitations listed in its result.
    - National results do not identify a specific line, wind farm or location. The network result is an input-gated TYTFS planning-case DC scenario, not live topology, a security verdict, or avoided-energy proof.
    - Keep constraint, curtailment and total dispatch-down separate; do not use them interchangeably.
    - Operator actions may only come from get_scenario_actions. An action there is only in scope, not safe or available. Recommend an exact action only when the results include the required action inputs plus reviewed network and safety evidence for it; otherwise explain the blockers.
    - Answer only what was asked. Times are UTC. Probabilities as percentages; energy in MWh with one decimal place.
    - Be concise and write for a control-room operator.
"""

SCENARIO_IDS = ("T1", "T2", "T3", "T4", "H1", "H2", "H3", "H4", "SNSP")
REPLAY_START = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)
REPLAY_END = datetime(2026, 1, 31, 23, 30, tzinfo=timezone.utc)
HISTORY_MESSAGES = 10  # past human/assistant messages sent to the model
_TIME_IN_TEXT = re.compile(r"\b(\d{4}-\d{2}-\d{2})[T ](\d{1,2}):(\d{2})")
_SCENARIO_IN_TEXT = re.compile(r"\b(T[1-4]|H[1-4]|SNSP)\b", re.I)


class ChatState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    selected_target: str | None
    scenario_ids: list[str] | None
    # Cached from the previous turn so a follow-up on the same time reuses them.
    tool_key: str | None
    tool_results: dict[str, dict]


# ---------- working out the inputs ----------

def _to_half_hour(value: datetime) -> datetime:
    value = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return value.replace(minute=0 if value.minute < 30 else 30, second=0, microsecond=0)


def resolve_target(text: str, selected: str | None, now: datetime | None = None) -> tuple[datetime, str]:
    """UI selection, else an explicit date-time in the text, else the next half-hour."""
    if selected:
        try:
            return _to_half_hour(datetime.fromisoformat(selected.replace("Z", "+00:00"))), "selected in the UI"
        except ValueError:
            pass
    if match := _TIME_IN_TEXT.search(text):
        date, hour, minute = match.groups()
        try:
            return _to_half_hour(datetime.fromisoformat(f"{date}T{int(hour):02d}:{minute}:00+00:00")), "stated in the message"
        except ValueError:
            pass
    now = now or datetime.now(timezone.utc)
    return _to_half_hour(now + timedelta(minutes=30)), "next half-hour (no time given)"


def resolve_scenarios(text: str, requested: list[str] | None) -> list[str]:
    """Scenario IDs from the request, else named in the text, else all locked IDs."""
    ids = [s.upper() for s in (requested or []) if s.upper() in SCENARIO_IDS]
    ids = ids or [m.upper() for m in _SCENARIO_IN_TEXT.findall(text)]
    return list(dict.fromkeys(ids)) or list(SCENARIO_IDS)


def _not_applicable(reason: str) -> dict:
    return {"status": "not_applicable", "reason": reason}


def plan_tool(name: str, target: datetime, scenario_ids: list[str], now: datetime) -> dict | None:
    """Arguments for one tool, or None when it does not fit this question."""
    iso = target.isoformat().replace("+00:00", "Z")
    in_replay = REPLAY_START <= target <= REPLAY_END
    future = target > now
    if name in ("get_dispatch_down_forecast", "get_dispatch_down_day"):
        return {"target_timestamp": iso} if in_replay else None
    if name == "check_constraint":
        return {"target_timestamp": iso, "horizon_hours": 1} if in_replay else None
    if name in ("get_current_constraint_forecast", "get_network_scenario"):
        return {"target_timestamp": iso} if future else None
    if name == "get_current_constraint_day":
        return {} if future else None
    if name == "get_scenario_actions":
        return {"scenario_ids": scenario_ids}
    return {"target_timestamp": iso}  # unknown tool: best effort


def _why_not(name: str, target: datetime) -> str:
    if name in ("get_dispatch_down_forecast", "get_dispatch_down_day", "check_constraint"):
        return f"historical replay covers January 2026 only; target is {target:%Y-%m-%d %H:%M} UTC"
    return f"forward forecast needs a future target; {target:%Y-%m-%d %H:%M} UTC has passed"


# ---------- trimming results ----------

def trim_result(name: str, result: Any) -> dict:
    """Keep what the model needs; drop bulky rows."""
    if not isinstance(result, dict):
        return {"value": result}
    if name == "get_dispatch_down_day" and isinstance(result.get("points"), list):
        points = result["points"]
        return {
            **{k: v for k, v in result.items() if k != "points"},
            "intervals": len(points),
            "total_expected_dispatch_down_mwh": round(sum(p.get("expected_dispatch_down_mwh", 0) for p in points), 1),
            "peak_intervals": sorted(points, key=lambda p: p.get("expected_dispatch_down_mwh", 0), reverse=True)[:5],
        }
    return result


def _status(result: dict) -> str:
    if result.get("status") == "not_applicable":
        return "not_applicable"
    return "error" if "error" in result else "ok"


# ---------- graph ----------

def build_graph(llm: BaseChatModel, tools: Sequence[BaseTool], checkpointer=None):
    by_name = {t.name: t for t in tools}

    def run_all_tools(state: ChatState) -> dict:
        question = str(state["messages"][-1].content) if state.get("messages") else ""
        now = datetime.now(timezone.utc)
        target, target_source = resolve_target(question, state.get("selected_target"), now)
        scenario_ids = resolve_scenarios(question, state.get("scenario_ids"))
        key = json.dumps([target.isoformat(), scenario_ids])
        if state.get("tool_key") == key and state.get("tool_results"):
            return {}  # same time and scenarios as last turn: reuse

        plans = {name: plan_tool(name, target, scenario_ids, now) for name in by_name}

        def run(name: str) -> dict:
            args = plans[name]
            if args is None:
                return _not_applicable(_why_not(name, target))
            try:
                return {"args": args, **trim_result(name, by_name[name].invoke(args))}
            except Exception as exc:  # one broken tool must not fail the turn
                logger.exception("Chat tool %s failed", name)
                return {"args": args, "error": f"Tool failed: {type(exc).__name__}"}

        with ThreadPoolExecutor(max_workers=max(1, len(by_name))) as pool:
            results = dict(zip(by_name, pool.map(run, by_name)))
        results["_inputs"] = {"target_utc": target.isoformat().replace("+00:00", "Z"),
                              "target_source": target_source, "scenario_ids": scenario_ids}
        return {"tool_key": key, "tool_results": results}

    def answer(state: ChatState) -> dict:
        results = state.get("tool_results") or {}
        prompt = SYSTEM_PROMPT
        if state.get("selected_target"):
            prompt += f"\n\nThe operator currently has {state['selected_target']} UTC selected in the UI; 'this time' refers to it."
        context = "Tool results (JSON):\n" + json.dumps(results, default=str)
        history = [m for m in state["messages"] if m.type in ("human", "ai")][-HISTORY_MESSAGES:]
        response = llm.invoke([SystemMessage(prompt), SystemMessage(context), *history])
        return {"messages": [response]}

    graph = StateGraph(ChatState)
    graph.add_node("run_all_tools", run_all_tools)
    graph.add_node("answer", answer)
    graph.add_edge(START, "run_all_tools")
    graph.add_edge("run_all_tools", "answer")
    graph.add_edge("answer", END)
    return graph.compile(checkpointer=checkpointer or MemorySaver())


def build_azure_llm(settings, *, timeout: int = 60, max_retries: int = 3) -> BaseChatModel:
    from langchain_openai import AzureChatOpenAI

    kwargs = dict(
        azure_endpoint=settings.endpoint,
        api_key=settings.api_key,
        azure_deployment=settings.deployment,
        api_version=settings.api_version,
        max_retries=max_retries,
        timeout=timeout,
    )
    if not settings.is_reasoning_model:
        kwargs["temperature"] = 0
    return AzureChatOpenAI(**kwargs)


# ---------- trace ----------

def tool_results_used(results: dict | None) -> list[str]:
    return [name for name, r in (results or {}).items() if not name.startswith("_") and _status(r) != "not_applicable"]


def _step_tools(node: str, update: dict) -> list[dict]:
    if node != "run_all_tools":
        return []
    results = update.get("tool_results") or {}
    return [{"name": name, "args": r.get("args"), "status": _status(r), "ok": _status(r) != "error"}
            for name, r in results.items() if not name.startswith("_")]


def _step_detail(node: str, update: dict) -> str:
    if node == "run_all_tools":
        results = update.get("tool_results")
        if not results:
            return "same time and scenarios as last turn; reused results"
        inputs = results.get("_inputs", {})
        tools = _step_tools(node, update)
        ran = sum(t["status"] != "not_applicable" for t in tools)
        return f"target {inputs.get('target_utc')} ({inputs.get('target_source')}); ran {ran} of {len(tools)} tools"
    if node == "answer":
        return "wrote the reply (1 model call)"
    return ""


def run_with_trace(graph, inputs: dict, config: dict) -> tuple[dict, list[dict]]:
    """Run one turn and record each node with its run time.

    Updates arrive as each node finishes, so the gap between them is that
    node's run time.
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
