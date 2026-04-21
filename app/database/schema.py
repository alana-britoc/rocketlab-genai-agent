import sqlite3
import os
from functools import lru_cache
from pathlib import Path

_BUSINESS_RULES = """
RELACIONAMENTOS ENTRE TABELAS
- fat_pedidos -> fat_itens_pedidos (id_pedido)
- fat_pedidos -> fat_pedido_total (id_pedido)
- fat_pedidos -> fat_avaliacoes_pedidos (id_pedido)
- fat_pedidos -> dim_consumidores (id_consumidor)
- fat_itens_pedidos -> dim_produtos (id_produto)
- fat_itens_pedidos -> dim_vendedores (id_vendedor)

REGRAS DE NEGOCIO E MAPEAMENTO
- Receita/Faturamento: SUM(preco_BRL + preco_frete) da tabela fat_itens_pedidos.
- Valor Pago: Use valor_total_pago_brl da tabela fat_pedido_total.
- Entrega no Prazo: Use a coluna entrega_no_prazo da tabela fat_pedidos (valores: 'Sim' ou 'Nao').
- Avaliacao: A coluna e 'avaliacao' na tabela fat_avaliacoes_pedidos (1 a 5).
- Status do Pedido: Use a coluna 'status' nas tabelas fat_pedidos ou fat_pedido_total.
- Datas: pedido_compra_timestamp (data da compra) e pedido_entregue_timestamp (entrega real).
- Localizacao: Coluna 'estado' nas tabelas dim_consumidores e dim_vendedores.
"""

def _read_schema_from_db(db_path: str) -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    lines = ["Schema real do banco de dados:\n"]
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()
        
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            count_str = f" ({row_count} linhas)"
        except:
            count_str = ""
            
        lines.append(f"Tabela: {table}{count_str}")
        for col in cols:
            name, ctype = col[1], col[2]
            lines.append(f"  - {name} ({ctype})")
        lines.append("")
        
    conn.close()
    return "\n".join(lines)

@lru_cache(maxsize=1)
def _cached_schema(db_path: str, mtime: float) -> str:
    return _read_schema_from_db(db_path)

def get_schema_description() -> str:
    db_path = os.getenv("DB_PATH", "banco.db")
    path = Path(db_path)
    if not path.exists():
        return f"Erro: Arquivo {db_path} nao encontrado."
    
    mtime = path.stat().st_mtime
    schema_body = _cached_schema(db_path, mtime)
    return schema_body + "\n" + _BUSINESS_RULES