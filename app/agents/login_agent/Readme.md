
---

# 🧾 README.md – Login Agent Powered by LangGraph & LangSmith


> **DISCLAIMER** – This repository is a **proof of concept**.
> It showcases a clean, conversational Agent that is easy to extend.

---

## 🧠 Overview

This project implements an **intelligent login agent** that interacts with users to collect and validate their identification data — specifically, **CPF**  and **health card number** — in a structured and automated way.

It leverages **LangGraph** to manage state transitions and **LangSmith** to monitor, debug, and evaluate executions. The agent identifies user intent, extracts data, validates it, and guides the user through the login flow conversationally.

---

## 🔧 Architecture

```
User Input
   ↓
LangGraph State Machine
   ├── detect_intent: detect the user's goal
   ├── extract: extract CPF and health card
   ├── provide/update/list: respond based on intent
   ├── confirm: check if data is complete
   └── invalid: handle invalid input
   ↓
LangSmith: Execution tracing and debugging
```

---

## 🔐 Functionality: Login Agent

This agent can:

* 🎯 **Detect user intent**: understand if the user is providing, updating, or listing information.
* 🧾 **Extract structured data**: pull CPF and health card numbers from free-text input.
* 🔍 **Validate formats**: ensure values match Brazilian standards (CPF + ABC123456789).
* 🧭 **Guide users**: provide feedback and prompt for missing data.
* ✅ **Confirm login**: complete once both required fields are successfully collected.

---

## 🔁 Login Flow Pipeline

1. **User Input**: The user types a message (e.g., "Here's my CPF...").
2. **Intent Detection (`detect_intent`)**:

   * Classifies as `provide`, `update`, `list`, or `invalid`.
3. **Information Extraction (`extract`)**:

   * Uses the LLM to extract CPF and health card numbers.
4. **Routing Logic**:

   * Sends the flow to the appropriate node (`provide`, `update`, `list`).
5. **Response Handling**:

   * `update`: updates a field.
   * `list`: summarizes collected data.
   * `provide`: checks what’s missing and asks for more.
6. **Confirmation (`confirm`)**:

   * Confirms completion if both CPF and health card are valid.
7. **Termination or Retry**:

   * Exits after 5 invalid attempts or successful login.

---

## 🧱 Tech Stack

* **LangChain**: for structured LLM pipelines and prompt management.
* **LangGraph**: for building an interactive, state-driven workflow.
* **LangSmith**: for tracing, evaluation, and observability.


---

## 📁 Project Structure

```
agente_login.py        # Main logic and LangGraph definition
llm_factory.py         # LLM selection and initialization

```

---

## ▶️ How to Run

```bash

# Run the agent
python agente_login.py
```

---

## 💬 Sample Interaction

**User Input:**

> Hello, my CPF is 123.456.789-10

**Agent Response:**

> 👍 I’ve received your CPF. Now I need your *health card number* (format ABC123456789).

---

## 🔍 LangSmith Integration

This agent is **LangSmith-ready**. When using `.with_structured_output()`, LangSmith captures the flow of data and prompts for full observability and debugging.

---

## 🚀 Future Improvements

* Add integration with a real authentication database
* Support multilingual interaction
* Validate against government APIs (e.g., Receita Federal)

---

## 👤 Author
By Arthur Scanoni


