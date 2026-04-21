"""
E-commerce analysis agent built with LangGraph + Gemini 2.5 Flash (or Flash Lite).
Model is configurable via GEMINI_MODEL in .env — use Flash Lite for higher free-tier quota.
"""

import os
import json
import time
import random
from typing import Any
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.tools import ALL_TOOLS
from app.agent.prompts import build_system_prompt

load_dotenv()

_sessions: dict[str, list] = {}
_last_call_ts: float = 0.0
MIN_DELAY_SECONDS = 3.0  


def _get_llm() -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GOOGLE_API_KEY não encontrada. "
            "Copie .env.example para .env e preencha sua chave."
        )
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.1,
    )


def _throttle():
    """Ensure a minimum gap between API calls to avoid hitting rate limits."""
    global _last_call_ts
    elapsed = time.time() - _last_call_ts
    if elapsed < MIN_DELAY_SECONDS:
        time.sleep(MIN_DELAY_SECONDS - elapsed)
    _last_call_ts = time.time()


def _build_graph():
    llm = _get_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)
    tool_node = ToolNode(ALL_TOOLS)

    def call_model(state: MessagesState):
        system = SystemMessage(content=build_system_prompt())
        messages = [system] + state["messages"]

        max_retries = 4
        for attempt in range(max_retries):
            try:
                _throttle()
                response = llm_with_tools.invoke(messages)
                return {"messages": [response]}
            except Exception as e:
                err = str(e)
                is_rate_limit = "429" in err or "quota" in err.lower() or "rate" in err.lower()
                if is_rate_limit and attempt < max_retries - 1:
                    wait = (2 ** (attempt + 1)) + random.uniform(0, 2)
                    print(f"[Rate limit] Aguardando {wait:.1f}s (tentativa {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                else:
                    raise

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


def chat(session_id: str, user_message: str) -> dict[str, Any]:
    graph = _get_graph()
    history = _sessions.get(session_id, [])
    history.append(HumanMessage(content=user_message))

    result = graph.invoke({"messages": history})
    new_messages = result["messages"]
    _sessions[session_id] = new_messages

    ai_response = ""
    sql_queries: list[str] = []
    query_results: list[dict] = []

    for msg in reversed(new_messages):
        if isinstance(msg, AIMessage) and msg.content:
            ai_response = msg.content
            break

    for msg in new_messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] == "execute_sql":
                    sql_queries.append(tc["args"].get("query", ""))

    for msg in new_messages:
        if isinstance(msg, ToolMessage):
            try:
                parsed = json.loads(msg.content)
                if parsed.get("status") == "success" and parsed.get("data"):
                    query_results.append({
                        "query": parsed.get("query", ""),
                        "columns": parsed.get("columns", []),
                        "data": parsed.get("data", []),
                        "rows": parsed.get("rows", 0),
                        "anonymized": parsed.get("anonymized", False),
                    })
            except (json.JSONDecodeError, AttributeError):
                pass

    return {
        "response": ai_response,
        "sql_queries": sql_queries,
        "query_results": query_results,
        "session_id": session_id,
    }


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


def get_session_history(session_id: str) -> list[dict]:
    messages = _sessions.get(session_id, [])
    history = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            history.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage) and msg.content:
            history.append({"role": "assistant", "content": msg.content})
    return history