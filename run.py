import sys
import os
import shutil
from pathlib import Path

def clear_pycache():
    for path in Path(".").rglob("__pycache__"):
        try:
            shutil.rmtree(path)
        except:
            pass

def check_env():
    errors = []
    
    if not os.getenv("GOOGLE_API_KEY"):
        from dotenv import load_dotenv
        load_dotenv()
        if not os.getenv("GOOGLE_API_KEY"):
            errors.append("GOOGLE_API_KEY nao encontrada no arquivo .env")

    db_path = os.getenv("DB_PATH", "banco.db")
    if not Path(db_path).exists():
        errors.append(f"Banco de dados nao encontrado: {db_path}")

    if errors:
        print("\nFalha na validacao de ambiente:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("Configuracao validada.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    clear_pycache()
    check_env()

    import uvicorn
    print("\nIniciando E-Commerce GenAI Agent")
    print("Interface: http://localhost:8000")
    print("API Docs:  http://localhost:8000/docs")
    print("Pressione Ctrl+C para encerrar\n")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )