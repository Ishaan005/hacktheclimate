import pytest

pytest.importorskip("langgraph")

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool

from pathlib import Path

from backend.app.chat.graph import build_graph, load_action_text


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
        AIMessage("High risk: 95.4% chance, 37.2 MWh expected (historical replay). Recommended action: A2"),
        AIMessage("Still 01:00 UTC on 24 Jan."),
        AIMessage("Still 01:00 UTC on 24 Jan."),
    ], seen=[])
    graph = build_graph(llm, [get_dispatch_down_forecast])
    config = {"configurable": {"thread_id": "t1"}}

    result = graph.invoke({"messages": [HumanMessage("Risk at 01:00 on the 24th?")], "selected_target": "2026-01-24T01:00"}, config)
    tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert tool_msgs and "0.954" in tool_msgs[0].content
    assert result["messages"][-1].content.startswith("High risk")
    assert "2026-01-24T01:00 UTC selected" in llm.seen[0][0].content
    assert "Candidate operator actions" in llm.seen[0][0].content
    assert "Recommended action: A2" in result["messages"][-1].content
    assert "final reply" in llm.seen[2][0].content

    follow_up = graph.invoke({"messages": [HumanMessage("Which time was that?")], "selected_target": None}, config)
    assert len(follow_up["messages"]) == 6  # history kept by the checkpointer


def test_action_list_loads_and_skips_comments():
    text = load_action_text()
    assert text.startswith("A1 |") and "#" not in text
    assert load_action_text(Path("/nonexistent")) == ""
