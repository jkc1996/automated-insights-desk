# 📊 Automated Data Insights Desk

A distributed, multi-agent AI system built to independently analyze local databases and generate formatted markdown reports. This project demonstrates an enterprise-grade architecture using Google's **Agent-to-Agent (A2A) protocol**, the **Model Context Protocol (MCP)**, and **LangGraph**.

## 🏗️ Architecture Overview



This system operates as a distributed microservice network rather than a single script. It uses a **Supervisor-Worker** (Hub and Spoke) model:

* **🧠 Router Client (The Orchestrator):** A LangGraph supervisor that interprets the user's prompt via a Gradio UI, reads the A2A Agent Cards of the workers, and dynamically routes tasks over HTTP. It maintains short-term memory using Redis.
* **🔎 Analyst Server (Worker 1):** An independent A2A HTTP server running a LangGraph subgraph. It connects to a local SQLite database using the official `@modelcontextprotocol/server-sqlite` to extract and analyze data.
* **📝 Publisher Server (Worker 2):** An independent A2A HTTP server running a LangGraph subgraph. It connects to the local filesystem using `@modelcontextprotocol/server-filesystem` to format and save Markdown reports.

## 🚀 Tech Stack

* **Orchestration:** [LangGraph](https://github.com/langchain-ai/langgraph) (State management and Subgraphs)
* **Communication:** [A2A SDK](https://github.com/google/a2a-sdk) (Agent-to-Agent Protocol & Agent Cards)
* **Tooling:** [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) via standard stdio servers
* **LLM Gateway:** [LiteLLM](https://github.com/BerriAI/litellm) (Local proxy routing to OpenAI models)
* **Observability:** [Langfuse](https://langfuse.com/) (Detailed tracing of LLM thoughts and tool calls)
* **Memory:** Redis (via `langgraph-checkpoint-redis`)
* **Frontend:** Gradio (Chat UI)

## 📂 Project Structure

```text
automated-insights-desk/
├── docker-compose.yml          # LiteLLM, Postgres, and Redis Stack infrastructure
├── litellm-config.yaml         # Model routing and proxy configuration
├── mcp_servers.json            # Tool definitions for SQLite and Filesystem
├── ui.py                       # Gradio Chat Interface
├── data/                       
│   └── dummy_data.db           # Local database for the Analyst
├── reports/                    # Output directory for the Publisher
├── analyst_server/             # Microservice 1: Data Extractor
├── publisher_server/           # Microservice 2: Markdown Writer
└── router_client/              # Microservice 3: Orchestrator & UI Backend
```

## ⚙️ Prerequisites

1.  **Python 3.10+**
2.  **Podman** (or Docker) for running the infrastructure stack.
3.  **Node.js (npx)** for running the official MCP server binaries.

## 🛠️ Setup Instructions

**1. Clone the repository and set up the environment**
```bash
git clone [https://github.com/your-username/automated-insights-desk.git](https://github.com/your-username/automated-insights-desk.git)
cd automated-insights-desk
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**2. Configure Environment Variables**
Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your_litellm_virtual_key
OPENAI_API_BASE=http://localhost:4000
DEFAULT_MODEL=gpt-4o-mini
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=[https://dev-smartpal.cybage.com](https://dev-smartpal.cybage.com)
REDIS_URI=redis://localhost:6379
```

**3. Start the Core Infrastructure**
Spin up the LiteLLM proxy, its PostgreSQL database, and the Redis cache:
```bash
podman compose up -d
```

## 🏃‍♂️ Running the System

Because this is a distributed system, you need to start the microservices independently. Open three separate terminal windows, activate the `.venv` in each, and run:

**Terminal 1: Start the Analyst Server**
```bash
python -m analyst_server.server
```

**Terminal 2: Start the Publisher Server**
```bash
python -m publisher_server.server
```

**Terminal 3: Start the UI / Router**
```bash
python ui.py
```
*Navigate to `http://localhost:7860` in your browser to start chatting with the insights desk!*