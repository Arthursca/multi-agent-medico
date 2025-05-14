# 🧾 README.md 

> **DISCLAIMER** – This repository is a **proof of concept**.
> It showcases a clean, modular RAG architecture that is easy to extend, but the current feature‑set is intentionally minimal.

---

## 🧠 Overview

This project implements a **Retrieval‑Augmented Generation (RAG)** pipeline that answers questions about health‑insurance plan documents.
It combines:

* **LangGraph** – state‑machine orchestration for query‑rewrite, retrieval and answer generation.&#x20;
* **LangChain** – prompt & LLM abstractions.
* **PostgreSQL + pgvector** – scalable vector storage.&#x20;
* **LangSmith** – end‑to‑end tracing and debugging.&#x20;

Even with the small scope, the project is split into clear layers (Embedding → VectorStore → Retriever → RAG Graph → Agent/CLI).
Adding new data sources, LLMs or post‑processing nodes is straightforward.

---

## 🔧 Architecture

```text
┌────────────┐
│   User     │
└─────┬──────┘
      │ query
      ▼
┌────────────┐
│  Agent     │ (agent_plano.py)
│  Router    │ relevance check
└─────┬──────┘
      │ relevant?
┌─────┴──────┐           no ──► Default reply
│  RAG       │           yes
│  Pipeline  │ rewrite → retrieve → generate
└─────┬──────┘
      │ answer
      ▼
┌────────────┐
│   User     │
└────────────┘
```

| Layer           | Responsibility                                     | Key files                   |
| --------------- | -------------------------------------------------- | --------------------------- |
| **Embedding**   | Create OpenAI embeddings with exponential back‑off | `embedder.py`               |
| **VectorStore** | Upsert & search (HNSW) in pgvector                 | `vector_store.py`, `db.py`  |
| **Retriever**   | Convert query → embedding and run top‑k search     | `retriever.py`              |
| **RAG Graph**   | LangGraph nodes: rewrite ▸ retrieve ▸ generate     | `rag_pipeline.py`           |
| **Agent**       | Checks relevance and triggers RAG                  | `agent_plano.py`            |
| **CLI**         | Terminal testing script                            | `query_pipeline.py`         |

---

## 🔐 Features

* **Query rewrite** to boost recall before retrieval.&#x20;
* **Vector search** (top‑k) over document chunks.&#x20;
* **Contextual answer generation** with the chosen LLM.
* **Automatic retries** on embedding failures (Tenacity).&#x20;
* **Structured logging** at every stage.
* **LangSmith observability** via `@traceable` decorators.&#x20;

> 🔸 *Limitations*: no automatic document ingestion yet and only basic semantic filters – ideal starting point for further work.

---

## 🔁 RAG Flow Step‑by‑Step

1. **User input** (`query`)
2. **Relevance check** (`AgentState.validate`) – *Yes/No*.&#x20;
3. **Rewrite** – prompt expands or clarifies the query.&#x20;
4. **Retrieve** – pgvector HNSW top‑k similarity.&#x20;
5. **Generate** – LLM composes answer with retrieved context.
6. **Return** answer to user.

---

## 🧱 Tech Stack

* **Python 3.11**
* **LangChain + LangGraph**
* **OpenAI API** (*text‑embedding‑3‑small*)
* **PostgreSQL 16 + pgvector 0.6.3**
* **SQLAlchemy 2**
* **LangSmith** for tracing

---

## 📁 Project Structure

```text
app/
└─ agents/health_plan_agent/tools/rag/
   ├─ embedding/       embedder.py
   ├─ vectorstore/     db.py, vector_store.py
   ├─ pipeline/
   │  ├─ retriever.py
   │  ├─ rag_pipeline.py
   │  └─ scripts/query_pipeline.py
   └─ utils/           logger.py, callbacks.py
agent_plano.py         # agent router
```

---

## ▶️ Quick Start

```bash
# 1. Copy environment variables
cp .env.example .env        # set OPENAI_API_KEY, DATABASE_URL, LANGSMITH_API_KEY …

# 2. Ask a sample question
python scripts/query_pipeline.py -q "Which exams does the plan cover?"
```

---

## 💬 Sample Interaction

> **User:** “What is the waiting period for a dermatology appointment?”
> **Agent:** “According to the Gold plan rules, there is no waiting period for outpatient appointments; coverage is immediate.”

---

## 🔍 LangSmith Integration

Every RAG graph run is wrapped with `@traceable`, which gives you:

* **Timeline** of nodes (`rewrite`, `retrieve`, `generate`)
* **Full prompt/response** visibility
* **Metrics** for duration and token usage

Set `LANGSMITH_API_KEY` in your `.env` and open the LangSmith dashboard.


---

## 👤 Author

Arthur Scanoni – *arthurscanoni.dev*

---

