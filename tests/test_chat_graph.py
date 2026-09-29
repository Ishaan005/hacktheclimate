import pytest

pytest.importorskip("langgraph")

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool

from backend.app.chat.graph import build_graph, run_with_trace
from backend.app.chat import tools as forecast_tools


class ScriptedModel(BaseChatModel):
    """Returns pre-set replies in order and records what it was sent."""

    replies: list
    seen: list = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(messages)
        return ChatResult(generations=[ChatGeneration(message=self.replies.pop(0))])


@tool
def get_dispatch_down_forecast(target_timestamp: str) -> dict:
    """Fake forecast."""
    return {"risk": "high", "event_probability": 0.954, "expected_dispatch_down_mwh": 37.2}


def test_agent_calls_tool_then_answers_and_remembers_thread():
    llm = ScriptedModel(replies=[
        AIMessage("", tool_calls=[{"name": "get_dispatch_down_forecast", "args": {"target_timestamp": "2026-01-24T01:00:00Z"}, "id": "c1"}]),
        AIMessage("High risk: 95.4% chance, 37.2 MWh expected (historical replay)."),
        AIMessage("Still 01:00 UTC on 24 Jan."),
    ], seen=[])
    graph = build_graph(llm, [get_dispatch_down_forecast])
    config = {"configurable": {"thread_id": "t1"}}

    result = graph.invoke({"messages": [HumanMessage("Risk at 01:00 on the 24th?")], "selected_target": "2026-01-24T01:00"}, config)
    tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert tool_msgs and "0.954" in tool_msgs[0].content
    assert result["messages"][-1].content.startswith("High risk")
    assert "2026-01-24T01:00 UTC selected" in llm.seen[0][0].content
    assert "Candidate operator actions" not in llm.seen[0][0].content
    assert "get_scenario_actions" in llm.seen[0][0].content

    follow_up = graph.invoke({"messages": [HumanMessage("Which time was that?")], "selected_target": None}, config)
    assert len(follow_up["messages"]) == 6


def test_trace_records_the_path_that_actually_ran():
    llm = ScriptedModel(replies=[
        AIMessage("", tool_calls=[{"name": "get_dispatch_down_forecast", "args": {"target_timestamp": "2026-01-24T01:00:00Z"}, "id": "c1"}]),
        AIMessage("High risk (historical replay)."),
        AIMessage("Hello."),
    ], seen=[])
    graph = build_graph(llm, [get_dispatch_down_forecast])
    config = {"configurable": {"thread_id": "trace"}}

    _, trace = run_with_trace(graph, {"messages": [HumanMessage("Risk?")], "selected_target": None}, config)
    assert [step["node"] for step in trace] == ["__start__", "agent", "tools", "agent", "__end__"]
    assert trace[1]["detail"] == "requested get_dispatch_down_forecast"
    assert trace[2]["detail"] == "ran get_dispatch_down_forecast"

    _, trace = run_with_trace(graph, {"messages": [HumanMessage("Hi")], "selected_target": None}, config)
    assert [step["node"] for step in trace] == ["__start__", "agent", "__end__"]


def test_chat_route_returns_the_trace(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.app.chat import routes

    llm = ScriptedModel(replies=[AIMessage("Hello.")], seen=[])
    monkeypatch.setattr(routes, "get_chat_graph", lambda: build_graph(llm, [get_dispatch_down_forecast]))
    app = FastAPI()
    app.include_router(routes.router)
    body = TestClient(app).post("/v1/chat", json={"message": "Hi"}).json()
    assert body["reply"] == "Hello."
    assert [step["node"] for step in body["trace"]] == ["__start__", "agent", "__end__"]


def test_current_constraint_tools_use_checked_snapshot(monkeypatch):
    snapshot = {
        "issue_time_utc": "2026-09-29T00:00:00Z",
        "generated_at_utc": "2026-09-29T06:15:00Z",
        "served_at_utc": "2026-09-29T10:00:00Z",
        "forecast_end_utc": "2026-09-30T06:00:00Z",
        "model": {"name": "gfs_constraint_final_candidate", "artifact_sha256": "abc"},
        "limitations": ["Experimental; August error exceeded zero forecast."],
        "forecasts": [
            {"target_time_utc": "2026-09-29T12:00:00Z", "expected_constraint_mwh": 5.0},
            {"target_time_utc": "2026-09-29T12:30:00Z", "expected_constraint_mwh": 8.0},
        ],
    }
    monkeypatch.setattr(forecast_tools, "_current_constraint_snapshot", lambda: snapshot)
    point = forecast_tools.get_current_constraint_forecast.invoke({"target_timestamp": "2026-09-29T12:30:00Z"})
    assert point["mode"] == "experimental_forward_forecast"
    assert point["forecast"]["expected_constraint_mwh"] == 8.0
    assert point["target"] == "national_constraint_mwh"
    day = forecast_tools.get_current_constraint_day.invoke({})
    assert day["sum_expected_constraint_mwh"] == 13.0
    assert day["peak_intervals"][0]["target_time_utc"] == "2026-09-29T12:30:00Z"
    assert "error" in forecast_tools.get_current_constraint_forecast.invoke({"target_timestamp": "2026-09-29T12:15:00Z"})
    assert "error" in forecast_tools.get_current_constraint_forecast.invoke({"target_timestamp": "2026-09-29T11:00:00Z"})


def test_current_constraint_tool_reports_missing_snapshot(monkeypatch):
    def missing():
        raise FileNotFoundError("latest.json")

    monkeypatch.setattr(forecast_tools, "_current_constraint_snapshot", missing)
    assert "unavailable" in forecast_tools.get_current_constraint_day.invoke({})["error"]


def test_scenario_action_tool_uses_decision_contract():
    result = forecast_tools.get_scenario_actions.invoke({"scenario_ids": ["T1"]})
    assert result["mode"] == "decision_action_contract"
    assert result["catalogue_status"] == "working_draft"
    by_id = {item["action_id"]: item for item in result["actions"]}
    assert by_id["FLEX_LOAD"]["execution_status"] == "planning_supported"
    assert "RESERVE_RAMP_ACTION" not in by_id


def test_graph_calls_current_model_tool(monkeypatch):
    monkeypatch.setattr(forecast_tools, "_current_constraint_snapshot", lambda: {
        "issue_time_utc": "2026-09-29T00:00:00Z", "generated_at_utc": "2026-09-29T06:15:00Z",
        "served_at_utc": "2026-09-29T10:00:00Z", "forecast_end_utc": "2026-09-30T06:00:00Z",
        "model": {"name": "gfs_constraint_final_candidate", "artifact_sha256": "abc"},
        "limitations": ["Experimental"],
        "forecasts": [{"target_time_utc": "2026-09-29T12:30:00Z", "expected_constraint_mwh": 8.0}],
    })
    llm = ScriptedModel(replies=[
        AIMessage("", tool_calls=[{"name": "get_current_constraint_forecast", "args": {"target_timestamp": "2026-09-29T12:30:00Z"}, "id": "c2"}]),
        AIMessage("Experimental national constraint forecast: 8.0 MWh."),
    ], seen=[])
    graph = build_graph(llm, forecast_tools.FORECAST_TOOLS)
    result = graph.invoke({"messages": [HumanMessage("What is the upcoming constraint at 12:30 UTC?")], "selected_target": None}, {"configurable": {"thread_id": "forward"}})
    messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(messages) == 1 and "experimental_forward_forecast" in messages[0].content
