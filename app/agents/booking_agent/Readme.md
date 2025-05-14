
---

# 🗓️ README.md – Appointment‑Scheduling Agent (LangGraph + PostgreSQL)

> **DISCLAIMER** – This repository is a **proof of concept**.
> It showcases a clean, LangGraph + PostgreSQL architecture that is easy to extend, but the current feature‑set is intentionally minimal.

---

## 🧠 Overview

This repository delivers an **intelligent medical‑appointment agent** that

* Retrieves doctors for three Brazilian capitals (São Paulo, Recife, Fortaleza) by specialty (nutrologo, psiquiatra, psicologo).
* Lets patients **list, create or cancel appointments** in natural language.
* Saves bookings in PostgreSQL while preventing schedule clashes.
* Scrapes Doctoralia on demand for up‑to‑date physician information.

LangGraph drives the conversational flow; scraping uses Beautiful Soup; bookings live in a relational database.

---

## 🔧 Architecture

```
User ↔ AgenteAgendamentos (state machine)
                │
                ├─ list_doctors          → ScrapeModule.scrape_doctors
                │                          (Doctoralia HTML ➜ structured list)
                │
                ├─ create_appointment    → PostgreSQL INSERT
                │
                ├─ list_appointments     → PostgreSQL SELECT
                │
                └─ cancel_appointment    → PostgreSQL UPDATE
                       ▲
                       │
        LangGraph RAG sub‑agent (rag_agendamento.py)
        └─ PARSE → VALIDATE → FETCH → RESPOND
```

---

## 🗂️ Key Modules

| File                    | Purpose                                                                                                                                         |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `rag_agendamento.py`    | LangGraph workflow that extracts the requested **specialty**, validates city & specialty, scrapes the web, and formats the reply.               |
| `scrape_module.py`      | Pure‑Python web scraper: builds a Doctoralia URL, parses each list item, returns `List[dict]` containing *name, CRM, address, etc.*             |
| `tools_agendamentos.py` | Wraps DB helpers and the RAG workflow as **LangChain tools** (`list_doctors`, `create_appointment`, `cancel_appointment`, `list_appointments`). |
| `agente_agendamento.py` | Top‑level, state‑aware chat agent that detects user intent and orchestrates the tools.                                                          |
| `llm_factory.py`        | Centralised LLM selector (OpenAI by default).                                                                                                   |

---

## 🩺 Functional Breakdown

### 1 · Doctor Discovery (`rag_agendamento.py`)

1. **PARSE** – An LLM function‑call extracts only the specialty (`"psychiatrist"`, `"psychologist"`, `"nutritionist"`).
2. **VALIDATE** – Rejects unsupported cities or specialties immediately.
3. **FETCH** – Calls `scrape_doctors(city, specialty)` and keeps the **top 5**.
4. **RESPOND** – Returns a bullet list or a graceful fallback message.

### 2 · Booking Tools (`tools_agendamentos.py`)

* `list_doctors(city, specialty)` – Runs the RAG agent synchronously.
* `create_appointment(doctor, specialty, datetime)` – Inserts if the slot is free.
* `cancel_appointment(appointment_id)` – Logical delete (status → *canceled*).
* `list_appointments()` – Returns every row for the hard‑coded `PATIENT_ID = 1`.

### 3 · Conversation Flow (`agente_agendamento.py`)

```
User: "I'd like to book an appointment."
        │
        ├─ Ask: "Doctor's name?"
        ├─ Ask: "Specialty?"
        ├─ Ask: "Date (YYYY‑MM‑DD)?"
        ├─ Ask: "Time (HH:MM)?"
        └─ Confirm: "Book Dr. X on 2025‑12‑31 at 14:30? (yes/no)"
```

Validation rules:

* **Dates must lie in the future** (`pydantic` validator).
* Conflicting slots trigger an immediate warning.
* At any point the user can abort by saying “cancel”.

---

## 🧱 Tech Stack

* **LangChain + LangGraph** – Orchestrated LLM pipelines & state machines.
* **PostgreSQL + psycopg2** – Durable appointment storage.
* **requests + Beautiful Soup 4** – Lightweight web scraping.
* **Python 3.11** – Type‑safe via `pydantic`.

---

## 📁 Project Structure

```
appointment_agent/
├─ agente_agendamento.py   # chat front‑end
├─ tools_agendamentos.py   # LangChain tools + DB helpers
├─ rag_agendamento.py      # LangGraph RAG workflow
├─ scrape_module.py        # Doctoralia scraper
├─ llm_factory.py          # selects the LLM provider
└─ README.md               # this file
```

---

## ▶️ Running Locally

```bash
# 1 · Environment
export POSTGRES_HOST=
export POSTGRES_DB=
export POSTGRES_USER=
export POSTGRES_PASS=

# 2 · Dependencies
pip install -r requirements.txt

# 3 · Initialise the DB
psql -U xxx -d xxx -f xxxx

# 4 · Start the chat agent
python agente_agendamento.py
```

When the CLI launches, you will first be asked for the **city** and then guided through the rest of the conversation.

---

## 💬 Example Interaction (CLI)

```
🗺️  Enter city (e.g., sao‑paulo):
> sao‑paulo
👤  Which specialist do you need?
> I need a psychologist

🤖  Here are some psychologists in São Paulo:

1. Dr. Alice Alves — Av. Paulista 1000  
2. Dr. Bruno Lima  — R. Haddock Lobo 200  
...
```

```
User: "list"
Agent: "Your appointments:
1) Dr. Alice Alves – psychologist on 2025‑06‑01 09:00 (scheduled)"
```

---

## 🔍 Observability with LangSmith

Wrap any `.ainvoke` call in `.with_config({"run_name": "appointment‑agent"})` and set `LANGCHAIN_TRACING_V2=1` to obtain live traces and metrics.

---

## 👤 Author

Created by **Arthur Scanoni** — PRs and issues are welcome!

---
