"""
FastAPI backend for the E-Commerce GenAI Agent.
Endpoints: chat, history, clear, suggestions, export, schema, insights
"""

import io
import uuid
import pandas as pd
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.agent.agent import chat, clear_session, get_session_history
from app.agent.guardrails import validate_sql, GuardrailViolation
from app.agent.evaluator import evaluate_response
from app.agent.insights import run_insights
from app.charts.generator import generate_chart, dataframe_from_result
from app.database.connection import query_to_dataframe, get_table_info
from app.database.schema import get_schema_description
from app.models.schemas import (
    ChatRequest, ChatResponse, QueryResult, EvaluationResult,
    HistoryResponse, HistoryMessage,
    SuggestionsResponse, ExportRequest,
    InsightItem, InsightsResponse,
)


app = FastAPI(
    title="E-Commerce GenAI Agent",
    description="Agente de análise de dados de e-commerce com Text-to-SQL via Gemini 2.5 Flash",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_PATH = Path(__file__).parent.parent / "frontend" / "index.html"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend():
    if FRONTEND_PATH.exists():
        return HTMLResponse(content=FRONTEND_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Frontend não encontrado. Adicione frontend/index.html</h1>")


@app.post("/chat", response_model=ChatResponse, tags=["Agent"])
async def chat_endpoint(request: ChatRequest, evaluate: bool = False):
    """
    Envia uma mensagem ao agente e recebe análise + SQL + gráfico.

    - **evaluate=true** — ativa avaliação automática da resposta (consome +1 chamada à API).
      Desabilitado por padrão para preservar cota do tier gratuito do Gemini.
    """
    try:
        result = chat(session_id=request.session_id, user_message=request.message)
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower():
            raise HTTPException(
                status_code=429,
                detail="Limite de requisições da API Gemini atingido. Aguarde alguns segundos e tente novamente. "
                       "Considere ativar o faturamento em https://aistudio.google.com para aumentar os limites."
            )
        raise HTTPException(status_code=500, detail=f"Erro no agente: {err}")

    query_results = [QueryResult(**qr) for qr in result.get("query_results", [])]

    chart = None
    for qr in reversed(result.get("query_results", [])):
        df = dataframe_from_result(qr)
        if not df.empty and len(df) > 1:
            chart = generate_chart(df)
            if chart:
                break

    evaluation = None
    sql_queries = result.get("sql_queries", [])
    if evaluate and sql_queries and result.get("response"):
        raw_eval = evaluate_response(
            question=request.message,
            sql=sql_queries[-1],
            response=result["response"],
        )
        if raw_eval:
            try:
                evaluation = EvaluationResult(**raw_eval)
            except Exception:
                pass

    return ChatResponse(
        response=result["response"],
        session_id=result["session_id"],
        sql_queries=sql_queries,
        query_results=query_results,
        chart=chart,
        evaluation=evaluation,
    )


@app.get("/history/{session_id}", response_model=HistoryResponse, tags=["Session"])
async def get_history(session_id: str):
    """Retorna o histórico de mensagens de uma sessão."""
    messages = get_session_history(session_id)
    return HistoryResponse(
        session_id=session_id,
        messages=[HistoryMessage(**m) for m in messages],
    )


@app.delete("/session/{session_id}", tags=["Session"])
async def delete_session(session_id: str):
    """Limpa o histórico de uma sessão (começa nova conversa)."""
    clear_session(session_id)
    return {"message": f"Sessão '{session_id}' limpa com sucesso."}


@app.get("/session/new", tags=["Session"])
async def new_session():
    """Gera um novo session_id único."""
    return {"session_id": str(uuid.uuid4())}



SUGGESTIONS = [
    "Quais são os 10 produtos mais vendidos?",
    "Qual a receita total por categoria de produto?",
    "Quantos pedidos existem por status?",
    "Qual o % de pedidos entregues no prazo por estado?",
    "Qual a média de avaliação geral dos pedidos?",
    "Quais os 10 vendedores com melhor avaliação média?",
    "Quais estados têm maior volume de pedidos e maior ticket médio?",
    "Quais estados têm maior atraso médio nas entregas?",
    "Quais produtos são mais vendidos por estado?",
    "Quais categorias têm maior taxa de avaliação negativa?",
    "Qual a evolução mensal da receita?",
    "Quais são os meios de pagamento mais utilizados?",
    "Qual o frete médio por estado?",
    "Quais categorias têm maior ticket médio?",
    "Quantos clientes únicos realizaram mais de 1 pedido?",
]


@app.get("/suggestions", response_model=SuggestionsResponse, tags=["Agent"])
async def get_suggestions():
    """Retorna sugestões de perguntas para o usuário."""
    return SuggestionsResponse(suggestions=SUGGESTIONS)



@app.get("/insights/debug", tags=["Agent"])
async def debug_insights():
    """Retorna as colunas reais de cada tabela — útil para diagnosticar falhas nos insights."""
    from app.agent.insights import debug_columns
    return debug_columns()


@app.get("/insights", response_model=InsightsResponse, tags=["Agent"])
async def get_insights():
    """
    Executa 5 análises automáticas pré-definidas e retorna resultados + gráficos.
    Útil como dashboard de overview sem precisar fazer perguntas.
    """
    try:
        items = run_insights()
        return InsightsResponse(insights=[InsightItem(**i) for i in items])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/export/csv", tags=["Export"])
async def export_csv(request: ExportRequest):
    """Executa uma query e retorna o resultado como arquivo CSV."""
    try:
        validate_sql(request.query)
        df = query_to_dataframe(request.query)
    except GuardrailViolation as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    stream = io.StringIO()
    df.to_csv(stream, index=False, encoding="utf-8")
    stream.seek(0)

    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resultado.csv"},
    )


@app.post("/export/excel", tags=["Export"])
async def export_excel(request: ExportRequest):
    """Executa uma query e retorna o resultado como arquivo Excel."""
    try:
        validate_sql(request.query)
        df = query_to_dataframe(request.query)
    except GuardrailViolation as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    stream = io.BytesIO()
    df.to_excel(stream, index=False, engine="openpyxl")
    stream.seek(0)

    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=resultado.xlsx"},
    )



@app.get("/schema", tags=["Database"])
async def get_schema():
    """Retorna o schema completo do banco de dados."""
    return {"schema": get_schema_description(), "tables": get_table_info()}



@app.get("/health", tags=["System"])
async def health():
    """Verifica se o servidor e o banco de dados estão operacionais."""
    try:
        from app.database.connection import get_connection
        conn = get_connection()
        conn.close()
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "model": "gemini-2.5-flash",
    }
