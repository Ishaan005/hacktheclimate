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


@tool
def get_current_constraint_day() -> dict:
    """Fake forward outlook."""
    return {"sum_expected_constraint_mwh": 1.0}


def test_runs_every_tool_then_answers_once_and_remembers_thread():
    llm = ScriptedModel(replies=[
        AIMessage("High risk: 95.4% chance, 37.2 MWh expected (historical replay)."),
        AIMessage("Still 01:00 UTC on 24 Jan."),
    ], seen=[])
    graph = build_graph(llm, [get_dispatch_down_forecast, get_current_constraint_day])
    config = {"configurable": {"thread_id": "t1"}}

    result = graph.invoke({"messages": [HumanMessage("Risk at 01:00 on the 24th?")], "selected_target": "2026-01-24T01:00"}, config)
    results = result["tool_results"]
    assert results["get_dispatch_down_forecast"]["event_probability"] == 0.954
    assert results["get_current_constraint_day"]["status"] == "not_applicable"
    assert result["messages"][-1].content.startswith("High risk")
    assert len(llm.seen) == 1  # one model call per question
    assert "2026-01-24T01:00 UTC selected" in llm.seen[0][0].content
    assert "0.954" in llm.seen[0][1].content
    assert not any(isinstance(m, ToolMessage) for m in result["messages"])

    follow_up = graph.invoke({"messages": [HumanMessage("Which time was that?")], "selected_target": "2026-01-24T01:00"}, config)
    assert len(follow_up["messages"]) == 4
    assert len(llm.seen) == 2


def test_trace_is_run_all_tools_then_answer():
    llm = ScriptedModel(replies=[AIMessage("High risk (historical replay)."), AIMessage("Hello.")], seen=[])
    graph = build_graph(llm, [get_dispatch_down_forecast, get_current_constraint_day])
    config = {"configurable": {"thread_id": "trace"}}

    _, trace = run_with_trace(graph, {"messages": [HumanMessage("Risk at 2026-01-24 01:00?")], "selected_target": None}, config)
    assert [step["node"] for step in trace] == ["__start__", "run_all_tools", "answer", "__end__"]
    statuses = {t["name"]: t["status"] for t in trace[1]["tools"]}
    assert statuses == {"get_dispatch_down_forecast": "ok", "get_current_constraint_day": "not_applicable"}
    assert "stated in the message" in trace[1]["detail"]

    _, trace = run_with_trace(graph, {"messages": [HumanMessage("Hi, same time 2026-01-24 01:00")], "selected_target": None}, config)
    assert "reused" in trace[1]["detail"]


def test_chat_route_returns_the_trace(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.app.chat import routes

    llm = ScriptedModel(replies=[AIMessage("Hello.")], seen=[])
    monkeypatch.setattr(routes, "get_chat_graph", lambda: build_graph(llm, [get_dispatch_down_forecast]))
    app = FastAPI()
    app.include_router(routes.router)
    body = TestClient(app).post("/v1/chat", json={"message": "Hi", "selected_target": "2026-01-24T01:00:00Z"}).json()
    assert body["reply"] == "Hello."
    assert body["tools_used"] == ["get_dispatch_down_forecast"]
    assert [step["node"] for step in body["trace"]] == ["__start__", "run_all_tools", "answer", "__end__"]


def test_target_and_scenario_resolution():
    from datetime import datetime, timezone

    from backend.app.chat.graph import resolve_scenarios, resolve_target

    now = datetime(2026, 9, 29, 10, 10, tzinfo=timezone.utc)
    assert resolve_target("x", "2026-01-24T01:10", now)[0].isoformat() == "2026-01-24T01:00:00+00:00"
    assert resolve_target("at 2026-09-30 18:45", None, now)[0].isoformat() == "2026-09-30T18:30:00+00:00"
    assert resolve_target("upcoming?", None, now)[0].isoformat() == "2026-09-29T10:30:00+00:00"
    assert resolve_scenarios("is this T2 or snsp", None) == ["T2", "SNSP"]
    assert resolve_scenarios("nothing", ["H1"]) == ["H1"]
    assert len(resolve_scenarios("nothing", None)) == 9


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


def test_graph_runs_current_model_tool_for_future_target(monkeypatch):
    monkeypatch.setattr(forecast_tools, "_current_constraint_snapshot", lambda: {
        "issue_time_utc": "2026-09-29T00:00:00Z", "generated_at_utc": "2026-09-29T06:15:00Z",
        "served_at_utc": "2026-09-29T10:00:00Z", "forecast_end_utc": "2099-09-30T06:00:00Z",
        "model": {"name": "gfs_constraint_final_candidate", "artifact_sha256": "abc"},
        "limitations": ["Experimental"],
        "forecasts": [{"target_time_utc": "2099-09-29T12:30:00Z", "expected_constraint_mwh": 8.0}],
    })
    llm = ScriptedModel(replies=[AIMessage("Experimental national constraint forecast: 8.0 MWh.")], seen=[])
    tools = [forecast_tools.get_current_constraint_forecast, forecast_tools.get_current_constraint_day, forecast_tools.check_constraint]
    graph = build_graph(llm, tools)
    result = graph.invoke({"messages": [HumanMessage("Constraint at 2099-09-29 12:30?")], "selected_target": None}, {"configurable": {"thread_id": "forward"}})
    results = result["tool_results"]
    assert results["get_current_constraint_forecast"]["mode"] == "experimental_forward_forecast"
    assert results["get_current_constraint_day"]["sum_expected_constraint_mwh"] == 8.0
    assert results["check_constraint"]["status"] == "not_applicable"
