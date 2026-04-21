# E-Commerce GenAI Agent

Agente de análise de dados de e-commerce com consulta em linguagem natural, geração automática de SQL e visualizações interativas.
---

## Visão Geral

O sistema permite que usuários não técnicos façam perguntas em sobre um banco de dados de e-commerce e recebam respostas estruturadas com análise textual, tabelas de dados e gráficos gerados automaticamente, sem escrever uma linha de SQL.

**Stack principal:** Gemini 2.5 Flash-Lite · LangGraph · FastAPI · SQLite · Plotly

---

## Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| Text-to-SQL | Converte perguntas em português para SQL via LLM |
| Memória de conversa | Contexto preservado entre turnos via LangGraph |
| Gráficos automáticos | Detecção de tipo (bar, line, pie, scatter) e renderização via Plotly |
| Guardrails de segurança | Apenas SELECT permitido — bloqueia DDL, DML e SQL injection |
| Anonimização de dados | IDs e CEPs mascarados automaticamente nos resultados |
| Dashboard de insights | 6 análises automáticas sem necessidade de perguntas |
| Avaliação automática | Score de qualidade da resposta via LLM (opt-in) |
| Interface de chat | Frontend web com tabelas, gráficos inline e exportação |
| Export CSV / Excel | Download direto de qualquer resultado da interface |
| API REST documentada | Swagger UI disponível em `/docs` |
| Schema dinâmico | Lê nomes reais das colunas do banco em runtime |

---

## Estrutura do Projeto

```
ecommerce-agent/
├── app/
│   ├── main.py                    # FastAPI — 11 endpoints
│   ├── agent/
│   │   ├── agent.py               # LangGraph ReAct loop + sessões em memória
│   │   ├── tools.py               # Ferramentas: execute_sql, get_schema, get_sample_data
│   │   ├── guardrails.py          # Validação e sanitização de queries SQL
│   │   ├── prompts.py             # System prompt com schema e regras de negócio
│   │   ├── anonymizer.py          # Mascaramento de dados sensíveis (IDs, CEPs)
│   │   ├── evaluator.py           # Avaliação automática de qualidade (opt-in)
│   │   └── insights.py            # Dashboard automático com detecção de schema
│   ├── database/
│   │   ├── connection.py          # Conexão SQLite thread-safe + helpers pandas
│   │   └── schema.py              # Schema lido dinamicamente via PRAGMA table_info
│   ├── charts/
│   │   └── generator.py           # Detecção de tipo de gráfico + renderização Plotly
│   └── models/
│       └── schemas.py             # Modelos Pydantic para validação de request/response
├── frontend/
│   └── index.html                 # Interface de chat (HTML/CSS/JS, sem build step)
├── notebooks/
│   └── demo.ipynb                 # Notebook de demonstração com 8 seções
├── tests/
│   ├── test_guardrails.py         # 31 testes dos guardrails de segurança
│   └── test_charts.py             # 8 testes de detecção de tipo de gráfico
├── banco.db                       # Banco de dados (não versionado — ver abaixo)
├── .env                           # Variáveis de ambiente (não versionado)
├── .env.example                   # Modelo de configuração
├── requirements.txt
├── run.py                         # Script de inicialização com validação de ambiente
├── inspect_schema.py              # Diagnóstico do schema real do banco
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Instalação e Execução

### Pré-requisitos

- Python 3.11 ou superior
- Chave de API do Google AI Studio: [aistudio.google.com](https://aistudio.google.com/)
- Arquivo `banco.db` disponibilizado pela Visagio

### Passo a passo

**1. Clone o repositório**

```bash
git clone https://github.com/alana-britoc/rocketlab-genai-agent.git
```

**2. Crie e ative o ambiente virtual**

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**3. Instale as dependências**

```bash
pip install -r requirements.txt
```

**4. Configure as variáveis de ambiente**

```bash
cp .env.example .env
```

Edite o arquivo `.env` com seus dados:

```env
GOOGLE_API_KEY=sua_chave_aqui
DB_PATH=banco.db
GEMINI_MODEL=gemini-2.5-flash-lite
```

**5. Posicione o banco de dados**

Coloque o arquivo `banco.db` na raiz do projeto, na mesma pasta do `README.md`.

**6. Inicie o servidor**

```bash
python run.py
```

O script valida a chave de API e o banco de dados antes de iniciar o servidor.

**7. Acesse a aplicação**

| URL | Descrição |
|---|---|
| `http://localhost:8000` | Interface de chat |
| `http://localhost:8000/docs` | Documentação interativa da API (Swagger UI) |
| `http://localhost:8000/redoc` | Documentação alternativa (ReDoc) |
| `http://localhost:8000/health` | Status do servidor e do banco |

### Execução via Docker

```bash
docker-compose up --build
```

O `banco.db` é montado como volume read-only no container.

---

## API REST

### Endpoints disponíveis

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/chat` | Envia mensagem ao agente |
| `GET` | `/history/{session_id}` | Retorna histórico de uma sessão |
| `DELETE` | `/session/{session_id}` | Limpa o histórico de uma sessão |
| `GET` | `/session/new` | Gera um novo session_id único |
| `GET` | `/suggestions` | Lista de perguntas sugeridas |
| `GET` | `/insights` | Executa o dashboard automático de análises |
| `GET` | `/insights/debug` | Retorna colunas reais de todas as tabelas |
| `POST` | `/export/csv` | Exporta resultado de uma query como CSV |
| `POST` | `/export/excel` | Exporta resultado de uma query como Excel |
| `GET` | `/schema` | Schema completo do banco de dados |
| `GET` | `/health` | Status do servidor |

### Exemplo de uso

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quais sao os 10 produtos mais vendidos?",
    "session_id": "minha-sessao"
  }'
```

**Avaliação automática (opt-in)** — consome uma chamada adicional à API:

```bash
curl -X POST "http://localhost:8000/chat?evaluate=true" \
  -H "Content-Type: application/json" \
  -d '{"message": "Receita total por categoria", "session_id": "s1"}'
```

---

## Segurança

O módulo `guardrails.py` valida toda query SQL antes da execução:

- **Whitelist de operações:** apenas `SELECT` e CTEs (`WITH ... SELECT`) são permitidos
- **Blacklist de keywords:** `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, `TRUNCATE`, `PRAGMA` e variantes são bloqueados incondicionalmente
- **Detecção de injeção:** comentários SQL (`--`, `/* */`) e múltiplos statements (`;`) são rejeitados
- **Limite de linhas:** máximo de 500 linhas por resultado
- **Limite de tamanho:** queries acima de 4.000 caracteres são rejeitadas

A camada de anonimização mascara automaticamente colunas sensíveis nos resultados:

- IDs de pedido, consumidor e vendedor: primeiros 8 caracteres + `-****`
- Prefixos de CEP: primeiros 3 dígitos + `**`

---

## Arquitetura

```
Requisição HTTP (POST /chat)
        |
        v
   FastAPI — validação Pydantic
        |
        v
  LangGraph Agent — Gemini 2.5 Flash-Lite
        |
        |-- Tool: execute_sql
        |       |-- Guardrails (validação + bloqueio)
        |       |-- SQLite (execução)
        |       |-- Anonymizer (mascaramento)
        |       `-- Retorno estruturado (JSON)
        |
        |-- Tool: get_schema
        |       `-- PRAGMA table_info em runtime
        |
        `-- Tool: get_sample_data
                `-- SELECT * LIMIT 5
        |
        v
  Resposta do agente (texto + SQL + dados)
        |
        v
  Chart Generator — detecção automática de tipo
        |
        v
  FastAPI Response (JSON)
        |
        v
  Frontend — renderização inline (Plotly)
```

---

## Testes

```bash
pytest tests/ -v
```

| Suite | Cobertura |
|---|---|
| `test_guardrails.py` | 31 casos — queries válidas, operações bloqueadas, edge cases |
| `test_charts.py` | 8 casos — detecção de tipo, geração de figura, dados vazios |

---

## Notebook de Demonstração

```bash
cd notebooks
jupyter notebook demo.ipynb
```

O notebook cobre 8 seções independentes: setup do ambiente, análise de vendas, logística, satisfação, conversa multi-turno, validação de guardrails, acesso direto ao banco e dashboard automático. Cada seção pode ser executada isoladamente.

---

## Diagnóstico

Se alguma análise do dashboard retornar "colunas não encontradas", use o endpoint de debug para inspecionar o schema real:

```bash
# Via HTTP
curl http://localhost:8000/insights/debug

# Via script
python inspect_schema.py
```

---

## Configuração avançada

| Variável | Padrão | Descrição |
|---|---|---|
| `GOOGLE_API_KEY` | — | Chave da API do Google AI Studio (obrigatória) |
| `DB_PATH` | `banco.db` | Caminho para o arquivo SQLite |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` | Modelo Gemini a utilizar |

Modelos suportados pela atividade: `gemini-2.5-flash` e `gemini-2.5-flash-lite`.

---

## Tech Stack

| Componente | Tecnologia |
|---|---|
| LLM | Gemini 2.5 Flash-Lite (Google AI) |
| Framework de agentes | LangGraph + LangChain |
| Backend | FastAPI + Uvicorn |
| Banco de dados | SQLite3 |
| Visualizações | Plotly |
| Processamento de dados | Pandas |
| Validação | Pydantic v2 |
| Segurança SQL | sqlparse |
| Frontend | HTML / CSS / JavaScript |

---
