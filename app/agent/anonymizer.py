"""
Anonimização de dados sensíveis nos resultados de queries.
Mascara IDs, CEPs e outros dados identificáveis antes de retornar ao usuário.
"""

import re
from typing import Any

_ID_COLUMNS = {
    "customer_id",
    "customer_unique_id",
    "seller_id",
    "order_id",
    "review_id",
    "product_id",
}

_ZIP_COLUMNS = {
    "customer_zip_code_prefix",
    "seller_zip_code_prefix",
}

_GEO_COLUMNS = {
    "customer_city",
    "seller_city",
}


def _mask_id(value: Any) -> str:
    """Mantém os 8 primeiros caracteres e mascara o restante."""
    s = str(value)
    if len(s) <= 8:
        return s
    return s[:8] + "-****"


def _mask_zip(value: Any) -> str:
    """Mantém os 3 primeiros dígitos e mascara os demais."""
    s = str(value).strip()
    if len(s) <= 3:
        return s
    return s[:3] + "**"


def anonymize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Aplica anonimização em uma linha do resultado."""
    result = {}
    for col, val in row.items():
        col_lower = col.lower()
        if val is None:
            result[col] = val
        elif col_lower in _ID_COLUMNS:
            result[col] = _mask_id(val)
        elif col_lower in _ZIP_COLUMNS:
            result[col] = _mask_zip(val)
        else:
            result[col] = val
    return result


def anonymize_results(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aplica anonimização em todos os registros de um resultado."""
    return [anonymize_row(row) for row in data]


def has_sensitive_columns(columns: list[str]) -> bool:
    """Retorna True se o resultado contém colunas sensíveis."""
    cols_lower = {c.lower() for c in columns}
    return bool(cols_lower & (_ID_COLUMNS | _ZIP_COLUMNS))
