"""
Guardrails de segurança para validação de queries SQL.
Garante que apenas operações de leitura (SELECT) sejam executadas.
"""

import re
import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DDL, DML


FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "REPLACE", "MERGE", "EXEC", "EXECUTE",
    "GRANT", "REVOKE", "ATTACH", "DETACH", "PRAGMA",
}

DANGEROUS_PATTERNS = [
    r"--",          
    r"/\*.*?\*/",    
    r";\s*\w",      
    r"xp_\w+",       
    r"LOAD_FILE",
    r"INTO\s+OUTFILE",
    r"INTO\s+DUMPFILE",
]

MAX_QUERY_LENGTH = 4000
MAX_RESULT_ROWS = 500


class GuardrailViolation(Exception):
    """Raised when a SQL query violates security guardrails."""
    pass


def validate_sql(query: str) -> str:
    """
    Validate and sanitize a SQL query.
    Returns the cleaned query string if valid.
    Raises GuardrailViolation if the query is not allowed.
    """
    if not query or not query.strip():
        raise GuardrailViolation("Query vazia não é permitida.")

    if len(query) > MAX_QUERY_LENGTH:
        raise GuardrailViolation(
            f"Query muito longa ({len(query)} chars). Máximo: {MAX_QUERY_LENGTH}."
        )

    clean = query.strip().rstrip(";")

    query_upper = clean.upper()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE | re.DOTALL):
            raise GuardrailViolation(
                f"Padrão não permitido detectado na query: '{pattern}'"
            )

    parsed = sqlparse.parse(clean)
    if not parsed:
        raise GuardrailViolation("Não foi possível analisar a query SQL.")

    for statement in parsed:
        _validate_statement(statement, query_upper)

    return clean


def _validate_statement(statement: Statement, query_upper: str) -> None:
    """Validate a single parsed SQL statement."""
    first_token = None
    for token in statement.tokens:
        if not token.is_whitespace:
            first_token = token
            break

    if first_token is None:
        raise GuardrailViolation("Statement vazio detectado.")

    token_normalized = first_token.normalized.upper()

    if token_normalized == "WITH":
        if "SELECT" not in query_upper:
            raise GuardrailViolation(
                "Queries WITH (CTE) devem conter um SELECT."
            )
        return  

    if token_normalized != "SELECT":
        raise GuardrailViolation(
            f"Apenas queries SELECT são permitidas. "
            f"Operação '{token_normalized}' não é autorizada."
        )

    for keyword in FORBIDDEN_KEYWORDS:
        pattern = rf"\b{keyword}\b"
        if re.search(pattern, query_upper):
            raise GuardrailViolation(
                f"Operação '{keyword}' não é permitida. "
                "Apenas consultas de leitura (SELECT) são autorizadas."
            )


def add_row_limit(query: str, limit: int = MAX_RESULT_ROWS) -> str:
    """
    Add a LIMIT clause to the query if it doesn't already have one.
    Protects against runaway queries returning millions of rows.
    """
    clean = query.strip().rstrip(";")
    if not re.search(r"\bLIMIT\b", clean, re.IGNORECASE):
        clean = f"{clean} LIMIT {limit}"
    return clean
