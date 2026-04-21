"""
Modo exploratório: análises automáticas — queries com colunas reais do banco.
"""

import sqlite3
from app.database.connection import query_to_dataframe, get_connection
from app.charts.generator import generate_chart


def _cols(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def _pick(available: list[str], *keywords: str) -> str | None:
    lower_map = {c.lower(): c for c in available}
    for kw in keywords:
        if kw.lower() in lower_map:
            return lower_map[kw.lower()]
    for kw in keywords:
        kw_s = kw.lower().replace("_", "")
        for col_l, col in lower_map.items():
            if kw_s in col_l.replace("_", "") or col_l.replace("_", "") in kw_s:
                return col
    return None

def _build_receita_categoria(conn) -> str | None:
    fi = _cols(conn, "fat_itens_pedidos")
    dp = _cols(conn, "dim_produtos")
    fp = _cols(conn, "fat_pedidos")

    price    = _pick(fi, "preco_BRL", "price", "preco", "valor", "valor_item")
    freight  = _pick(fi, "preco_frete", "freight_value", "frete", "freight")
    prod_fi  = _pick(fi, "id_produto", "product_id", "produto_id")
    prod_dp  = _pick(dp, "id_produto", "product_id", "produto_id")
    category = _pick(dp, "categoria_produto", "product_category_name", "categoria", "category")
    ord_fi   = _pick(fi, "id_pedido", "order_id", "pedido_id")
    ord_fp   = _pick(fp, "id_pedido", "order_id", "pedido_id")
    status   = _pick(fp, "status", "order_status", "pedido_status")

    if not all([price, prod_fi, prod_dp, category, ord_fi, ord_fp]):
        return None

    revenue  = f"fi.{price}" if not freight else f"fi.{price} + fi.{freight}"
    s_filter = f"AND fp.{status} NOT IN ('canceled','cancelado','unavailable','indisponivel')" if status else ""

    return f"""
        SELECT dp.{category} AS categoria,
               ROUND(SUM({revenue}), 2) AS receita_total
        FROM fat_itens_pedidos fi
        JOIN dim_produtos dp ON fi.{prod_fi} = dp.{prod_dp}
        JOIN fat_pedidos fp ON fi.{ord_fi} = fp.{ord_fp}
        WHERE dp.{category} IS NOT NULL {s_filter}
        GROUP BY dp.{category}
        ORDER BY receita_total DESC
        LIMIT 10
    """

def _build_pedidos_status(conn) -> str | None:
    fp = _cols(conn, "fat_pedidos")
    status = _pick(fp, "status", "order_status", "pedido_status", "situacao")
    if not status:
        return None
    return f"""
        SELECT {status} AS status, COUNT(*) AS total
        FROM fat_pedidos
        GROUP BY {status}
        ORDER BY total DESC
    """

def _build_avaliacao_mensal(conn) -> str | None:
    fa = _cols(conn, "fat_avaliacoes_pedidos")
    fp = _cols(conn, "fat_pedidos")

    score  = _pick(fa, "avaliacao", "review_score", "score", "nota", "rating")
    ord_fa = _pick(fa, "id_pedido", "order_id", "pedido_id")
    ord_fp = _pick(fp, "id_pedido", "order_id", "pedido_id")
    dt_col = _pick(fp, "pedido_compra_timestamp", "order_purchase_timestamp",
                       "purchase_date", "data_compra", "data_pedido", "data_criacao",
                       "created_at", "timestamp", "compra")

    if not all([score, ord_fa, ord_fp, dt_col]):
        return None

    return f"""
        SELECT strftime('%Y-%m', fp.{dt_col}) AS mes,
               ROUND(AVG(fa.{score}), 2) AS avg_score
        FROM fat_avaliacoes_pedidos fa
        JOIN fat_pedidos fp ON fa.{ord_fa} = fp.{ord_fp}
        WHERE fp.{dt_col} IS NOT NULL
        GROUP BY mes
        ORDER BY mes
    """

def _build_ticket_estado(conn) -> str | None:
    fp = _cols(conn, "fat_pedidos")
    dc = _cols(conn, "dim_consumidores")
    ft = _cols(conn, "fat_pedido_total")

    cust_fp = _pick(fp, "id_consumidor", "customer_id", "cliente_id")
    cust_dc = _pick(dc, "id_consumidor", "customer_id", "cliente_id")
    state   = _pick(dc, "estado", "customer_state", "state", "uf")
    ord_fp  = _pick(fp, "id_pedido", "order_id", "pedido_id")
    ord_ft  = _pick(ft, "id_pedido", "order_id", "pedido_id")
    payment = _pick(ft, "valor_total_pago_brl", "payment_value", "valor", "total", "amount")
    status  = _pick(fp, "status", "order_status", "pedido_status")

    if not all([cust_fp, cust_dc, state, ord_fp, ord_ft, payment]):
        return None

    s_filter = f"AND fp.{status} IN ('entregue','delivered')" if status else ""

    return f"""
        SELECT dc.{state} AS estado,
               ROUND(SUM(ft.{payment}) / COUNT(DISTINCT fp.{ord_fp}), 2) AS ticket_medio,
               COUNT(DISTINCT fp.{ord_fp}) AS total_pedidos
        FROM fat_pedidos fp
        JOIN dim_consumidores dc ON fp.{cust_fp} = dc.{cust_dc}
        JOIN fat_pedido_total ft ON fp.{ord_fp} = ft.{ord_ft}
        WHERE 1=1 {s_filter}
        GROUP BY dc.{state}
        ORDER BY ticket_medio DESC
        LIMIT 10
    """

def _build_atraso_estado(conn) -> str | None:
    fp = _cols(conn, "fat_pedidos")
    dc = _cols(conn, "dim_consumidores")

    cust_fp      = _pick(fp, "id_consumidor", "customer_id", "cliente_id")
    cust_dc      = _pick(dc, "id_consumidor", "customer_id", "cliente_id")
    state        = _pick(dc, "estado", "customer_state", "state", "uf")
    ord_fp       = _pick(fp, "id_pedido", "order_id", "pedido_id")
    on_time      = _pick(fp, "entrega_no_prazo", "on_time", "no_prazo", "delivered_on_time")
    delivered    = _pick(fp, "pedido_entregue_timestamp", "order_delivered_customer_date",
                             "data_entrega", "entrega_cliente", "dt_entrega")
    estimated    = _pick(fp, "data_estimada_entrega", "order_estimated_delivery_date",
                             "prazo_entrega", "data_prazo", "estimated_date")
    status       = _pick(fp, "status", "order_status", "pedido_status")

    if not all([cust_fp, cust_dc, state, ord_fp]):
        return None

    s_filter = f"AND fp.{status} IN ('entregue','delivered')" if status else ""

    if on_time:
        return f"""
            SELECT dc.{state} AS estado,
                   COUNT(*) AS total_entregues,
                   SUM(CASE WHEN fp.{on_time} = 0 THEN 1 ELSE 0 END) AS atrasados,
                   ROUND(100.0 * SUM(CASE WHEN fp.{on_time} = 0 THEN 1 ELSE 0 END)
                         / COUNT(*), 1) AS pct_atraso
            FROM fat_pedidos fp
            JOIN dim_consumidores dc ON fp.{cust_fp} = dc.{cust_dc}
            WHERE fp.{on_time} IS NOT NULL {s_filter}
            GROUP BY dc.{state}
            HAVING total_entregues >= 30
            ORDER BY pct_atraso DESC
            LIMIT 10
        """

    if not all([delivered, estimated]):
        return None

    return f"""
        SELECT dc.{state} AS estado,
               COUNT(*) AS total_entregues,
               SUM(CASE WHEN fp.{delivered} > fp.{estimated} THEN 1 ELSE 0 END) AS atrasados,
               ROUND(100.0 * SUM(CASE WHEN fp.{delivered} > fp.{estimated} THEN 1 ELSE 0 END)
                     / COUNT(*), 1) AS pct_atraso
        FROM fat_pedidos fp
        JOIN dim_consumidores dc ON fp.{cust_fp} = dc.{cust_dc}
        WHERE fp.{delivered} IS NOT NULL AND fp.{estimated} IS NOT NULL {s_filter}
        GROUP BY dc.{state}
        HAVING total_entregues >= 30
        ORDER BY pct_atraso DESC
        LIMIT 10
    """

def _build_top_vendedores(conn) -> str | None:
    fi = _cols(conn, "fat_itens_pedidos")
    dv = _cols(conn, "dim_vendedores")

    seller_fi  = _pick(fi, "id_vendedor", "seller_id", "vendedor_id")
    seller_dv  = _pick(dv, "id_vendedor", "seller_id", "vendedor_id")
    name_dv    = _pick(dv, "nome_vendedor", "seller_name", "nome", "name")
    price      = _pick(fi, "preco_BRL", "price", "preco", "valor")
    freight    = _pick(fi, "preco_frete", "freight_value", "frete")
    ord_fi     = _pick(fi, "id_pedido", "order_id", "pedido_id")

    if not all([seller_fi, seller_dv, price, ord_fi]):
        return None

    revenue   = f"fi.{price}" if not freight else f"fi.{price} + fi.{freight}"
    name_col  = f"dv.{name_dv}" if name_dv else f"dv.{seller_dv}"
    join_part = f"JOIN dim_vendedores dv ON fi.{seller_fi} = dv.{seller_dv}" if seller_dv else ""
    select_name = f"{name_col} AS vendedor," if name_dv else f"fi.{seller_fi} AS vendedor,"

    if not seller_dv:
        return f"""
            SELECT {seller_fi} AS vendedor,
                   COUNT(DISTINCT {ord_fi}) AS total_pedidos,
                   ROUND(SUM({revenue}), 2) AS receita_total
            FROM fat_itens_pedidos fi
            GROUP BY {seller_fi}
            ORDER BY receita_total DESC
            LIMIT 10
        """

    return f"""
        SELECT {select_name}
               COUNT(DISTINCT fi.{ord_fi}) AS total_pedidos,
               ROUND(SUM({revenue}), 2) AS receita_total
        FROM fat_itens_pedidos fi
        {join_part}
        GROUP BY fi.{seller_fi}
        ORDER BY receita_total DESC
        LIMIT 10
    """

def debug_columns() -> dict:
    conn = get_connection()
    tables = ["fat_itens_pedidos", "fat_pedidos", "fat_pedido_total",
              "fat_avaliacoes_pedidos", "dim_produtos", "dim_consumidores", "dim_vendedores"]
    result = {t: _cols(conn, t) for t in tables}
    conn.close()
    return result

_BUILDERS = [
    ("receita_categoria", "Receita por Categoria",      "Top 10 categorias por receita total (itens + frete)",      _build_receita_categoria),
    ("pedidos_status",    "Pedidos por Status",          "Distribuição de todos os pedidos por status",              _build_pedidos_status),
    ("avaliacao_mensal",  "Avaliação Média Mensal",      "Evolução da nota média de avaliação ao longo do tempo",    _build_avaliacao_mensal),
    ("ticket_estado",     "Ticket Médio por Estado",     "Top 10 estados com maior ticket médio de compra",          _build_ticket_estado),
    ("atraso_estado",     "Taxa de Atraso por Estado",   "% de pedidos entregues com atraso por estado",             _build_atraso_estado),
    ("top_vendedores",    "Top 10 Vendedores",           "Vendedores com maior receita total gerada",                _build_top_vendedores),
]

def run_insights() -> list[dict]:
    conn = get_connection()
    results = []

    for insight_id, title, description, builder in _BUILDERS:
        item: dict = {
            "id": insight_id, "title": title, "description": description,
            "sql": "", "columns": [], "data": [], "rows": 0, "chart": None, "error": None,
        }
        try:
            sql = builder(conn)
            if not sql:
                item["error"] = "Colunas necessárias não encontradas no banco de dados."
                results.append(item)
                continue
            item["sql"] = sql.strip()
            df = query_to_dataframe(sql)
            item["columns"] = df.columns.tolist()
            item["data"] = df.to_dict(orient="records")
            item["rows"] = len(df)
            if not df.empty and len(df) > 1:
                item["chart"] = generate_chart(df, title=title)
        except Exception as e:
            item["error"] = str(e)
        results.append(item)

    conn.close()
    return results
