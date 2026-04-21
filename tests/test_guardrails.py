"""
Unit tests for SQL guardrails.
Run with: pytest tests/test_guardrails.py -v
"""

import pytest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agent.guardrails import validate_sql, add_row_limit, GuardrailViolation

VALID_QUERIES = [
    "SELECT * FROM fat_pedidos",
    "SELECT COUNT(*) FROM dim_consumidores",
    "SELECT product_id, product_category_name FROM dim_produtos LIMIT 10",
    """
    SELECT
        c.customer_state,
        COUNT(DISTINCT p.order_id) AS total_pedidos,
        ROUND(AVG(t.payment_value), 2) AS ticket_medio
    FROM fat_pedidos p
    JOIN dim_consumidores c ON p.customer_id = c.customer_id
    JOIN fat_pedido_total t ON p.order_id = t.order_id
    WHERE p.order_status = 'delivered'
    GROUP BY c.customer_state
    ORDER BY total_pedidos DESC
    """,
    "SELECT order_id FROM fat_pedidos WHERE order_status = 'canceled'",
    "WITH top AS (SELECT seller_id FROM fat_itens_pedidos GROUP BY seller_id) SELECT * FROM top",
]


@pytest.mark.parametrize("query", VALID_QUERIES)
def test_valid_queries_pass(query):
    """Valid SELECT queries must not raise."""
    result = validate_sql(query)
    assert result is not None
    assert len(result) > 0

BLOCKED_QUERIES = [
    ("DELETE FROM fat_pedidos", "DELETE"),
    ("INSERT INTO fat_pedidos VALUES (1)", "INSERT"),
    ("UPDATE dim_produtos SET product_weight_g = 0", "UPDATE"),
    ("DROP TABLE fat_pedidos", "DROP"),
    ("CREATE TABLE hack (id INTEGER)", "CREATE"),
    ("ALTER TABLE dim_consumidores ADD COLUMN cpf TEXT", "ALTER"),
    ("TRUNCATE TABLE fat_avaliacoes_pedidos", "TRUNCATE"),
    ("SELECT * FROM fat_pedidos; DROP TABLE fat_pedidos", "múltiplos statements"),
    ("PRAGMA table_info(fat_pedidos)", "PRAGMA"),
    ("", "vazia"),
    ("   ", "vazia"),
]


@pytest.mark.parametrize("query,reason", BLOCKED_QUERIES)
def test_blocked_queries_raise(query, reason):
    """Forbidden queries must raise GuardrailViolation."""
    with pytest.raises(GuardrailViolation, match=".+"):
        validate_sql(query)

def test_add_row_limit_adds_limit():
    query = "SELECT * FROM fat_pedidos"
    result = add_row_limit(query, limit=100)
    assert "LIMIT 100" in result.upper()

def test_add_row_limit_does_not_duplicate():
    query = "SELECT * FROM fat_pedidos LIMIT 50"
    result = add_row_limit(query, limit=500)
    assert result.upper().count("LIMIT") == 1

def test_add_row_limit_strips_semicolon():
    query = "SELECT * FROM fat_pedidos;"
    result = add_row_limit(query)
    assert not result.strip().endswith(";")

def test_query_too_long_raises():
    long_query = "SELECT " + "a" * 5000 + " FROM fat_pedidos"
    with pytest.raises(GuardrailViolation, match="longa"):
        validate_sql(long_query)

def test_lowercase_forbidden_blocked():
    with pytest.raises(GuardrailViolation):
        validate_sql("delete from fat_pedidos")

def test_mixed_case_forbidden_blocked():
    with pytest.raises(GuardrailViolation):
        validate_sql("DeLeTe FROM fat_pedidos")