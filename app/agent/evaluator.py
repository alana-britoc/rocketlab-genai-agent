"""
Avaliação automática das respostas do agente.
DESABILITADO por padrão para preservar cota da API.
Ative passando evaluate=true na requisição /chat.
"""

import re
import json
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

_EVAL_PROMPT = """Você é um avaliador de qualidade de sistemas Text-to-SQL.
Avalie a resposta do agente. Responda APENAS com JSON válido, sem texto extra.

Pergunta: {question}
SQL gerado: {sql}
Resposta: {response}

JSON esperado:
{{"sql_quality": <1-5>, "answer_relevance": <1-5>, "confidence": "alta"|"media"|"baixa", "caveat": "<string ou null>", "overall": <1-5>}}"""


def evaluate_response(
    question: str,
    sql: str,
    response: str,
) -> Optional[dict]:
    """
    Faz uma chamada leve ao LLM para avaliar a qualidade da resposta.
    Consome 1 request da cota — use apenas quando necessário.
    Retorna None silenciosamente em caso de erro ou rate limit.
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0,
        )

        prompt = _EVAL_PROMPT.format(
            question=question[:300],
            sql=sql[:600] if sql else "Nenhum SQL",
            response=response[:600],
        )

        result = llm.invoke([HumanMessage(content=prompt)])
        raw = result.content.strip()
        raw = re.sub(r"```[a-z]*\n?", "", raw).replace("```", "").strip()

        parsed = json.loads(raw)
        required = {"sql_quality", "answer_relevance", "confidence", "overall"}
        if not required.issubset(parsed.keys()):
            return None
        return parsed

    except Exception:
        return None

