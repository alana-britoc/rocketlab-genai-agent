import sqlite3
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "banco.db")


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection to the e-commerce database."""
    path = Path(DB_PATH)
    if not path.exists():
        raise FileNotFoundError(
            f"Banco de dados não encontrado em '{DB_PATH}'. "
            "Certifique-se de que o arquivo banco.db está na raiz do projeto."
        )
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def query_to_dataframe(sql: str) -> pd.DataFrame:
    """Execute a SQL query and return a pandas DataFrame."""
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn)


def get_table_info() -> dict[str, list[dict]]:
    """Return column metadata for all tables in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    schema: dict[str, list[dict]] = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [{"name": row[1], "type": row[2]} for row in cursor.fetchall()]
        schema[table] = cols

    conn.close()
    return schema
