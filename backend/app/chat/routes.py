from __future__ import annotations

import uuid
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import BaseModel, Field

from .config import get_settings
from .graph import build_azure_llm, build_graph, run_with_trace
from .tools import FORECAST_TOOLS

router = APIRouter(prefix="/v1/chat", tags=["chat assistant"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: str | None = None
    selected_target: str | None = None


class TraceStep(BaseModel):
    node: str
    detail: str


class ChatResponse(BaseModel):
    thread_id: str
    reply: str
    tools_used: list[str]
    model: str
    # Nodes that actually ran this turn, in order, from __start__ to __end__.
    trace: list[TraceStep] = []


@lru_cache(maxsize=1)
def get_chat_graph():
    settings = get_settings()
    if not settings.configured:
        raise RuntimeError("Azure OpenAI is not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in .env.")
    return build_graph(build_azure_llm(settings), FORECAST_TOOLS)


@router.get("/status")
def chat_status():
    settings = get_settings()
    return {"configured": settings.configured, "model": settings.deployment, "api_version": settings.api_version}


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        graph = get_chat_graph()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 12}
    try:
        before = len(graph.get_state(config).values.get("messages", []))
        result, trace = run_with_trace(
            graph,
            {"messages": [HumanMessage(request.message)], "selected_target": request.selected_target},
            config,
        )
    except Exception as exc:  # surface rate limits clearly; the endpoint is shared by all teams
        name = type(exc).__name__
        if name == "RateLimitError":
            raise HTTPException(429, "Azure OpenAI is busy (shared rate limit). Try again shortly.") from exc
        if name in {"AuthenticationError", "PermissionDeniedError"}:
            raise HTTPException(502, "Azure OpenAI rejected the key. Check AZURE_OPENAI_API_KEY.") from exc
        if name == "NotFoundError":
            raise HTTPException(502, "Deployment not found. Check AZURE_OPENAI_DEPLOYMENT.") from exc
        raise

    new_messages = result["messages"][before:]
    tools_used = [m.name for m in new_messages if isinstance(m, ToolMessage) and m.name]
    reply = next((m.content for m in reversed(new_messages) if isinstance(m, AIMessage) and m.content), "")
    return ChatResponse(thread_id=thread_id, reply=str(reply), tools_used=tools_used, model=get_settings().deployment, trace=trace)
