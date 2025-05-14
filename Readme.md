---

# 🖥️ README – Streamlit Front‑End & Multi‑Agent Orchestration

---

## 🌐 High‑Level Overview

This repository delivers a **patient self‑service portal** built with **Streamlit** that talks to three independent LangGraph/LangChain agents:

1. **Login Agent** – securely collects CPF + health‑card number.
2. **Health‑Plan Agent** – RAG pipeline that answers coverage questions.
3. **Booking Agent** – schedules, lists, or cancels medical appointments.

`app.py` is the glue: it drives the chat UI, persists state in `st.session_state`, and dynamically routes every user message to the appropriate agent.&#x20;

---

## 🏗️ Runtime Architecture

```text
                    ┌───────────────────────┐
                    │   Streamlit Front‑End │
                    │  (app.py ‑ chat UI)   │
                    └───────────┬───────────┘
                                │
             selects provider   ▼
    ┌───────────────────────────────────────────┐
    │  LLM Factory (OpenAI | Claude | …)        │
    └─────────────────┬─────────────────────────┘
                      │ shared llm instance
┌───────────────┬─────┴──────┬──────────────────┐
│ Login Agent   │ HealthPlan │ Booking Agent    │
│ (LangGraph)   │ Agent      │ (Finite‑state    │
│               │ (RAG)      │    object)       │
└───────────────┴────────────┴──────────────────┘
```

* **Session Modes**: `"login" → "main" → "booking"` govern which agent receives the next user utterance.
* **Persistent Conversation**: messages are appended to `st.session_state["chat_history"]` and replayed on every rerun to render the chat scrollback.&#x20;

---

## 🔀 Message‑Routing Life‑Cycle

### 1. Login Mode

1. **Initial Greeting** – Streamlit seeds the chat asking for CPF & health card.
2. Every user message is fed into the **compiled LangGraph** (`compiled_graph.invoke(state)`), which returns an updated state containing: extracted data, inferred intent, and a `confirmed` flag once both fields are valid.&#x20;
3. After successful confirmation, the app queries Postgres for the patient record; if found, it switches `mode = "main"` and greets the user.&#x20;

### 2. Main Mode

* `classify_intent()` asks the LLM to label the message as **plan**, **booking**, **sair**, or **desconhecido**.&#x20;
* **Health‑Plan Questions** → forwarded into the RAG graph (`graph_plano.invoke({...})`).&#x20;
* **“Agendamento”** → creates an instance of `AgenteAgendamentos`, pushes helpful usage hints, and flips the session `mode` to `"booking"`.

### 3. Booking Mode

`AgenteAgendamentos.processar_mensagem()` implements a mini finite‑state workflow that elicits doctor, specialization, date & time, hits tool endpoints (`listar_medicos`, `agendar_consulta`, `cancelar_agendamento`), and confirms or aborts.&#x20;

* Users can exit back to Main by typing **sair / cancelar / encerrar** – the app sets `mode = "main"` and destroys the agent instance.&#x20;

---

## ⚙️ Key Implementation Details

| Concern                 | Implementation                                                                                                                                                                 |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **LLM Provider Switch** | Sidebar radio toggles between `"openai"` and `"claude"`; the chosen provider is injected into all agents via `init_llm()` functions before any conversation starts.            |
| **Input Handling**      | `builtins.input` is monkey‑patched with a Streamlit wrapper so LangGraph agents can still call `input()` in CLI style while running in a web app.                              |
| **State Isolation**     | Each agent keeps its own internal graph/object state; the Streamlit session variable `mode` is the single switch that prevents cross‑talk.                                     |
| **Database Access**     | `psycopg2` connection pool for patient lookup ≠ agent execution. All write operations (e.g., appointment insert) happen inside tool functions referenced by the booking agent. |

---

## 🏃‍♂️ Running Locally

```bash
# 1. Install deps
pip install -r requirements.txt

# 2. Export secrets (OpenAI, Postgres, etc.)
export OPENAI_API_KEY=...
export POSTGRES_HOST=...
export POSTGRES_DB=...
export POSTGRES_USER=...
export POSTGRES_PASS=...

# 3. Launch Streamlit
streamlit run app.py
```
## 🚀 Example

![exemplo](/img/image.png)

---

## 🧪 Sample End‑to‑End Session

| Speaker       | Message                                                             |
| ------------- | ------------------------------------------------------------------- |
| **Assistant** | “Olá! Please enter your CPF and health‑card number (ABC123456789).” |
| **User**      | “CPF 123.456.789‑10”                                                |
| **Assistant** | “👍 Got your CPF. Now give me your health‑card.”                    |
| **User**      | “Card ABC123456789”                                                 |
| **Assistant** | “✅ Login successful! Ask about **plan** or **agendamento**.”        |
| **User**      | “Agendar consulta com cardiologista.”                               |
| **Assistant** | “Sure! Doctor’s name?” → …full booking flow…                        |

---

## 📈 Observability

All agents are instrumented with the **LangSmith** tracer (`traceable` decorator or `.with_structured_output()`) so you can inspect each prompt, model response, and tool call in the LangSmith UI.&#x20;

---

##  Next Steps

* Persist booking data to the same Postgres instance.
* Add push notifications (SMS / email) on appointment confirmation.
* Internationalize content (PT‑BR ↔ EN).

---

## 👤 Author

Created by **Arthur Scanoni** – contributions welcome!
