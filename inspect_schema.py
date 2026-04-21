import sqlite3
import sys
from pathlib import Path

def inspect(db_path: str = "banco.db"):
    path = Path(db_path)
    if not path.exists():
        print(f"Erro: Arquivo nao encontrado: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "="*60)
    print(f"Schema do banco: {path.resolve()}")
    print("="*60 + "\n")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        print("Aviso: Nenhuma tabela encontrada no banco.")
        sys.exit(1)

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]

        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()

        print(f"Tabela: {table} ({count} linhas)")
        print(f"  {'CID':<4} {'NOME':<40} {'TIPO':<15} {'PK'}")
        print(f"  {'-'*4} {'-'*40} {'-'*15} {'--'}")
        for col in cols:
            cid, name, ctype, _, _, pk = col
            pk_mark = "PK" if pk else ""
            print(f"  {cid:<4} {name:<40} {ctype:<15} {pk_mark}")
        print()

    print("\n" + "="*60)
    print("Amostra de dados (1 linha por tabela)")
    print("="*60 + "\n")

    for table in tables:
        cursor.execute(f"SELECT * FROM {table} LIMIT 1")
        row = cursor.fetchone()
        cursor.execute(f"PRAGMA table_info({table})")
        col_names = [c[1] for c in cursor.fetchall()]
        if row:
            print(f"Tabela: {table}")
            for name, val in zip(col_names, row):
                preview = str(val)[:70] + ("..." if len(str(val)) > 70 else "")
                print(f"  {name}: {preview}")
            print()

    conn.close()
    print("Diagnostico concluido.\n")

if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "banco.db"
    inspect(db)