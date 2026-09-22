<div align="center">

# 🚀 Personal AI Action Agent
### *Autonomous Multi-MCP Architecture for GitHub & LinkedIn*

<p align="center">
  <a href="https://readme-typing-svg.demolab.com">
    <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&pause=1200&color=22C55E&center=true&vCenter=true&width=680&lines=Model+Context+Protocol+(MCP)+%2B+LangGraph;Autonomous+GitHub+Auditing+%2B+12-Section+READMEs;Safe+Developer+LinkedIn+Post+Publishing;100%25+Human-in-the-Loop+(HITL)+Dry-Run+Gates;11+Standard+JSON-RPC+MCP+Tools+Integrated" alt="Typing SVG" />
  </a>
</p>

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Standard%20JSON--RPC-8A2BE2?style=for-the-badge&logo=anthropic&logoColor=white)](https://modelcontextprotocol.io/)
[![LangGraph](https://img.shields.io/badge/Orchestrator-LangGraph%200.2+-FF6F00?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit%201.30+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Chroma RAG](https://img.shields.io/badge/Vector%20Store-Chroma%20RAG-00CED1?style=for-the-badge)](https://www.trychroma.com/)
[![Tests](https://img.shields.io/badge/Tests-100%25%20Passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](file:///e:/GITHUB_MCP/tests)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

<br/>

[🌟 Overview](#-overview) •
[🏗️ Architecture](#-system-architecture) •
[🛠️ 11 MCP Tools](#-11-mcp-tools-suite) •
[🛡️ HITL Safety Gates](#-safety--human-in-the-loop-hitl) •
[💻 Web Interface](#-interactive-web-dashboard) •
[⚡ Quickstart](#-quickstart) •
[🧪 Verification](#-automated-testing)

---

</div>

<br/>

## 🌟 Overview

The **Personal AI Action Agent** is a multi-service AI application built on the **Model Context Protocol (MCP)**, **LangGraph**, and **Retrieval-Augmented Generation (RAG)**. 

It safely bridges an autonomous AI agent with external development and professional networks:
* 🔍 **Repository Improvement Agent**: Gathers live tree metadata and AST configurations, runs semantic RAG queries, drafts a comprehensive 12-section `README.md`, and interactively proposes targeted GitHub issues.
* 📢 **Developer Post Synthesizer**: Extracts real repository architecture, highlights genuine technical challenges, generates optional graphics, and publishes authentic developer updates to LinkedIn.
* 💼 **Qualitative Profile Auditor**: Evaluates developer headlines, summaries, and skill stacks with high-impact, narrative recommendations (**strictly zero gimmicky numerical scores**).
* 🛡️ **Absolute Mutation Safety**: Every external write operation (`create_issue`, `create_post`, `delete_post`, `update_profile`) defaults to `dry_run=True` and requires explicit human approval via LangGraph state gates.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    User(["👤 User / Developer"])
    
    subgraph Interfaces ["🖥️ Presentation Layer"]
        Streamlit["Streamlit Web UI<br/>(frontend/app.py)"]
        CLI["Action Agent CLI<br/>(backend/main.py)"]
    end

    subgraph LangGraphEngine ["🧠 LangGraph Orchestrator"]
        AgentLoop["Autonomous Reasoning Node<br/>StateGraph: MessagesState"]
        HITL_Issue{"🛡️ Issue Approval Gate<br/>StateGraph"}
        HITL_Post{"🛡️ Post Approval Gate<br/>StateGraph"}
    end

    subgraph MultiMCPClient ["🔌 Multi-MCP Client Layer"]
        SessionScope["multi_mcp_session_scope<br/>Concurrent AsyncExitStack (stdio)"]
    end

    subgraph MCPServers ["⚡ Model Context Protocol Servers"]
        GH_Server["🐙 GitHub MCP Server<br/>(mcp_servers.github.server)<br/>6 Tools"]
        LI_Server["💼 LinkedIn MCP Server<br/>(mcp_servers.linkedin.server)<br/>5 Tools"]
    end

    subgraph ExternalAPIs ["🌐 External Services"]
        GitHubAPI[("GitHub REST API<br/>v3 / Repos & Issues")]
        LinkedInAPI[("LinkedIn REST API<br/>v2 OpenID & Posts 202401")]
    end

    User ==> Streamlit
    User ==> CLI
    Streamlit ==> AgentLoop
    CLI ==> AgentLoop
    AgentLoop ==> SessionScope
    SessionScope -.-> GH_Server
    SessionScope -.-> LI_Server

    AgentLoop -.-> HITL_Issue
    AgentLoop -.-> HITL_Post

    HITL_Issue -- Approved --> GH_Server
    HITL_Post -- Approved --> LI_Server
    
    GH_Server ==> GitHubAPI
    LI_Server ==> LinkedInAPI

    classDef cClient fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef cOrch fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#fff;
    classDef cMcp fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff;
    classDef cHitl fill:#701a75,stroke:#f472b6,stroke-width:2px,color:#fff;
    classDef cExt fill:#1f2937,stroke:#9ca3af,stroke-width:1px,color:#fff;

    class Streamlit,CLI cClient;
    class AgentLoop cOrch;
    class HITL_Issue,HITL_Post cHitl;
    class GH_Server,LI_Server cMcp;
    class GitHubAPI,LinkedInAPI cExt;
```

---

## 🛠️ 11 MCP Tools Suite

All tools are standard JSON-RPC 2.0 endpoints registered over `stdio` via `FastMCP`. They are automatically loaded into LangChain tools using `langchain-mcp-adapters`.

### 🐙 1. GitHub MCP Server (`mcp_servers.github.server`)
| # | Tool Name | Parameters | Safety / Mode | Description |
|:---:|:---|:---|:---:|:---|
| `01` | `get_repository` | `repo_url` | 🟢 Read-Only | Fetches metadata (stars, forks, primary language, license). |
| `02` | `get_repository_tree` | `repo_url`, `branch?`, `filter_ignored?` | 🟢 Read-Only | Recursive file tree filtering build noise (`node_modules`, `dist`, binaries). |
| `03` | `read_file` | `repo_url`, `file_path`, `branch?` | 🟢 Read-Only | Reads file contents with strict byte guardrails. |
| `04` | `search_repository` | `repo_url`, `query`, `max_results?` | 🟢 Read-Only | Code & documentation search with path hierarchy fallback. |
| `05` | `get_issues` | `repo_url`, `state?`, `max_issues?` | 🟢 Read-Only | Queries existing open/closed community issues. |
| `06` | `create_issue` | `repo_url`, `title`, `body`, `dry_run?` | 🔴 **HITL Action** | Creates a GitHub issue (requires human confirmation). |

### 💼 2. LinkedIn MCP Server (`mcp_servers.linkedin.server`)
| # | Tool Name | Parameters | Safety / Mode | Description |
|:---:|:---|:---|:---:|:---|
| `07` | `get_profile` | `raw?` | 🟢 Read-Only | Fetches verified identity via OpenID Connect (`GET /v2/userinfo`). |
| `08` | `analyze_profile` | `headline?`, `about?`, `skills?`, `projects?` | 🟢 Read-Only | Descriptive career feedback (**strictly no numerical scores**). |
| `09` | `create_post` | `content`, `image_url?`, `dry_run?` | 🔴 **HITL Action** | Publishes posts via official REST API (`POST /rest/posts`). |
| `10` | `delete_post` | `post_id`, `dry_run?` | 🔴 **HITL Action** | Destructive action: Deletes post via `/rest/posts/{urn}`. |
| `11` | `update_profile` | `headline?`, `about?`, `dry_run?` | 🔴 **HITL Action** | Prepares diffs & transparently enforces official API constraints. |

---

## 🛡️ Safety & Human-in-the-Loop (HITL)

> [!IMPORTANT]
> **Zero Accidental External Mutations**
> No issue is created on GitHub and no post is published on LinkedIn without passing through an explicit Human-in-the-Loop (HITL) approval gate.

```mermaid
sequenceDiagram
    autonumber
    actor Developer as 👤 Human Developer
    participant Agent as 🧠 LangGraph Agent
    participant Gate as 🛡️ HITL StateGraph Gate
    participant MCP as ⚡ MCP Action Tool
    participant API as 🌐 External API (GitHub/LinkedIn)

    Developer->>Agent: Request Action (e.g., "Post project update")
    Agent->>Agent: Synthesize grounded payload
    Agent->>Gate: Transfer to HITL Gate (user_approved=None, dry_run=True)
    Gate-->>Developer: 📋 Display Proposed Payload & Action Preview
    
    alt User Denies or Cancels
        Developer->>Gate: ❌ Reject (user_approved=False)
        Gate->>Gate: Route to abort node
        Gate-->>Developer: 🛑 Action safely cancelled. Zero mutations occurred.
    else User Confirms
        Developer->>Gate: ✅ Approve (user_approved=True)
        Gate->>MCP: Execute Action Tool
        MCP->>API: Authenticated External Call
        API-->>MCP: Mutation Result
        MCP-->>Developer: 🎉 Success Verification (Post URN / Issue URL)
    end
```

---

## 💻 Interactive Web Dashboard

The application includes a 7-tab Streamlit dashboard:

<div align="center">

| Tab | Feature | Description |
|:---:|:---|:---|
| **1** | 📊 **Audit & Improvements** | Factual health check, documentation score, and prioritized suggestions. |
| **2** | 📝 **Generated README** | Complete 12-section production `README.md` with instant copy-to-clipboard. |
| **3** | 📂 **Repository Tree** | Interactive directory tree with size breakdowns and noise filtering. |
| **4** | 🛡️ **Propose Issue (HITL)** | Interactive issue drafting with dry-run verification and manual execution. |
| **5** | 📢 **Post to LinkedIn (HITL)** | Grounded developer post generation with live preview and approval gate. |
| **6** | 💼 **LinkedIn Profile Auditor** | Strategic profile optimization suggestions without gimmicky scoring. |
| **7** | 💬 **Ask Multi-MCP Agent** | Interactive agent capable of cross-service reasoning across GitHub and LinkedIn. |

</div>

---

## ⚡ Quickstart

### 1. One-Click Launch (Windows)
Double-click `start_all.bat` or run:
```powershell
.\start_all.bat
```
*Automatically validates your environment, activates virtual environments, opens `http://localhost:8501`, and boots the server.*

---

### 2. Manual Setup

#### Clone & Install Dependencies
```powershell
git clone https://github.com/your-username/Personal-AI-Action-Agent.git
cd Personal-AI-Action-Agent
pip install -r requirements.txt
```

#### Configure Environment
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```

Configure your credentials in `.env`:
```ini
# GitHub Token (5,000 req/hr)
GITHUB_TOKEN=ghp_your_github_token_here

# LLM Providers (Google Gemini, OpenAI, or Groq)
GOOGLE_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key

# LinkedIn Integration (set LINKEDIN_MOCK=true for instant offline testing)
LINKEDIN_MOCK=true
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_ACCESS_TOKEN=
```

#### Start the Streamlit Web Application
```powershell
streamlit run frontend/app.py
```

---

### 3. Command-Line Interface (CLI)

#### Audit a GitHub Repository:
```powershell
python backend/main.py octocat/Hello-World
```

#### Draft a Grounded LinkedIn Post:
```powershell
python backend/main.py --post octocat/Hello-World
```

#### Run Profile Audit:
```powershell
python backend/main.py --profile
```

#### Query the Autonomous Multi-MCP Agent:
```powershell
python backend/main.py --agent "Inspect octocat/Hello-World and draft an elevator pitch for my LinkedIn summary"
```

*Add `-y` / `--yes` to auto-approve prompts non-interactively (defaults to safe dry-run mode).*

---

## 🧪 Automated Testing

All features, MCP tool discovery handshakes, and HITL state flows are covered by comprehensive automated tests:

```powershell
# Run the entire test suite
pytest -v

# Run targeted MCP server tests
pytest tests/test_linkedin_mcp.py tests/test_mcp_phase8.py -v
```

<details>
<summary><b>🔍 Click to view Test Suite Coverage (100% Passing)</b></summary>

```text
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-9.1.1, pluggy-1.6.0
collected 35 items

tests/test_github_tools.py .........................                    [ 71%]
tests/test_linkedin_mcp.py ............                                 [ 85%]
tests/test_mcp_phase1.py .                                              [ 88%]
tests/test_mcp_phase2.py .                                              [ 91%]
tests/test_mcp_phase6.py ...                                            [ 97%]
tests/test_mcp_phase8.py .                                              [100%]

======================== 35 passed in 14.22s (100%) ========================
```
</details>

---

## 🔒 Security & Privacy Guarantees

* 🛡️ **Zero Browser Scraping**: Adheres 100% to LinkedIn's developer terms. No Selenium, Playwright, or cookie extraction.
* 🔐 **Secret Redaction**: Zero API keys or tokens are ever embedded in prompts, logs, or source code.
* 📦 **Decoupled Architecture**: Subprocesses communicate exclusively through standard JSON-RPC 2.0 messages over `stdio`.

---

<div align="center">

Built with ❤️ using **LangGraph**, **Model Context Protocol (MCP)**, and **Streamlit**.

</div>
