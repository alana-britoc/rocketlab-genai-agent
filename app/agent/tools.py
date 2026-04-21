"""
LangChain tools available to the e-commerce analysis agent.
"""

import json
import pandas as pd
from typing import Annotated
from langchain_core.tools import tool

from app.database.connection import query_to_dataframe, get_table_info
from app.database.schema import get_schema_description
from app.agent.guardrails import validate_sql, add_row_limit, GuardrailViolation
from app.agent.anonymizer import anonymize_results, has_sensitive_columns


@tool
def execute_sql(
    query: Annotated[str, "Query SQL SELECT para executar no banco de dados de e-commerce"]
) -> str:
    """
    Executa uma query SQL SELECT no banco de dados de e-commerce e retorna os resultados.
    Use esta ferramenta para responder qualquer pergunta que envolva dados.
    Apenas queries SELECT são permitidas.
    """
    try:
        clean_query = validate_sql(query)

        limited_query = add_row_limit(clean_query)

        df = query_to_dataframe(limited_query)

        if df.empty:
            return json.dumps({
                "status": "success",
                "rows": 0,
                "columns": [],
                "data": [],
                "query": limited_query,
                "message": "A query retornou zero resultados."
            })

        columns = df.columns.tolist()
        data = df.to_dict(orient="records")
        anonymized = anonymize_results(data)
        was_anonymized = has_sensitive_columns(columns)

        return json.dumps({
            "status": "success",
            "rows": len(df),
            "columns": columns,
            "data": anonymized,
            "query": limited_query,
            "anonymized": was_anonymized,
            "message": f"{len(df)} linha(s) retornada(s)." + (" Dados sensíveis anonimizados." if was_anonymized else "")
        }, default=str, ensure_ascii=False)

    except GuardrailViolation as e:
        return json.dumps({
            "status": "error",
            "error_type": "guardrail",
            "message": f" Operação bloqueada pelos guardrails de segurança: {str(e)}"
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "execution",
            "message": f"Erro ao executar a query: {str(e)}"
        })


@tool
def get_schema() -> str:
    """
    Retorna o schema completo do banco de dados: tabelas, colunas e relacionamentos.
    Use esta ferramenta quando precisar relembrar a estrutura do banco antes de escrever uma query.
    """
    return get_schema_description()

@tool
def get_sample_data(
    table_name: Annotated[str, "Nome da tabela para amostrar (ex: fat_pedidos, dim_produtos)"]
) -> str:
    """
    Retorna uma amostra de 5 linhas de uma tabela específica.
    Útil para entender o formato dos dados antes de escrever queries complexas.
    """
    valid_tables = {
        "dim_consumidores", "dim_produtos", "dim_vendedores",
        "fat_pedidos", "fat_pedido_total", "fat_itens_pedidos", "fat_avaliacoes_pedidos"
    }

    if table_name not in valid_tables:
        return json.dumps({
            "status": "error",
            "message": f"Tabela '{table_name}' não existe. Tabelas válidas: {sorted(valid_tables)}"
        })

    try:
        df = query_to_dataframe(f"SELECT * FROM {table_name} LIMIT 5")
        return json.dumps({
            "status": "success",
            "table": table_name,
            "columns": df.columns.tolist(),
            "sample": df.to_dict(orient="records")
        }, default=str, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


ALL_TOOLS = [execute_sql, get_schema, get_sample_data]