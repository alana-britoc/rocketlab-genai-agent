from pydantic import BaseModel, Field
from typing import Any, Optional

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default")

class QueryResult(BaseModel):
    query: str
    columns: list[str]
    data: list[dict[str, Any]]
    rows: int
    anonymized: bool = False

class EvaluationResult(BaseModel):
    sql_quality: int
    answer_relevance: int
    confidence: str
    caveat: Optional[str]
    overall: int

class ChatResponse(BaseModel):
    response: str
    session_id: str
    sql_queries: list[str] = []
    query_results: list[QueryResult] = []
    chart: Optional[dict[str, Any]] = None
    evaluation: Optional[EvaluationResult] = None

class HistoryMessage(BaseModel):
    role: str
    content: str

class HistoryResponse(BaseModel):
    session_id: str
    messages: list[HistoryMessage]

class SuggestionsResponse(BaseModel):
    suggestions: list[str]

class ExportRequest(BaseModel):
    query: str

class InsightItem(BaseModel):
    id: str
    title: str
    description: str
    sql: str
    columns: list[str]
    data: list[dict[str, Any]]
    rows: int
    chart: Optional[dict[str, Any]]
    error: Optional[str]

class InsightsResponse(BaseModel):
    insights: list[InsightItem]