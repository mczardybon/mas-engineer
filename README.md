<p align="center">
  <br>
  <img src="https://via.placeholder.com/120x120/1a1a2e/ffffff?text=🦆" width="120" style="border-radius: 20px;">
  <br>
  <h1 align="center">MAS-Engineer</h1>
  <h3 align="center">Build Multi-Agent Systems by Talking, Not Coding</h3>
  <p align="center">
    <em>The world's first natural-language Multi-Agent System generator.<br>
    Ships with 48 ready-to-use agents, self-improvement, and 5-stage recovery.<br>
    You bring the idea. It builds the system.</em>
  </p>
</p>

<p align="center">
  <a href="#quick-start">⚡ Quick Start</a> •
  <a href="#what-makes-it-different">🆚 Why It Exists</a> •
  <a href="#overview">🎬 Demo</a> •
  <a href="#use-cases">💼 Use Cases</a> •
  <a href="#philosophy">🧠 Philosophy</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/agents-48-success?style=for-the-badge" alt="Agents">
  <img src="https://img.shields.io/badge/tools-50-success?style=for-the-badge" alt="Tools">
  <img src="https://img.shields.io/badge/self--improvement-8_stages-blue?style=for-the-badge" alt="Self-Improvement">
  <img src="https://img.shields.io/badge/recovery-5_stages-orange?style=for-the-badge" alt="Recovery">
  <img src="https://img.shields.io/badge/rules-23-red?style=for-the-badge" alt="Rules">
  <img src="https://img.shields.io/badge/runtime-Goose-purple?style=for-the-badge" alt="Goose">
</p>

---

## 🚀 TL;DR — Get a Multi-Agent System in 10 Seconds

```bash
./install.sh                    # → Installs into Goose
goose run --recipe dev-mas-engineer  # → Start talking
# Then:
# "Create a multi-agent system for my startup"
# "Researcher, writer, and reviewer agents"
# "Set up the dashboard"
# Done.
```

**No Python. No APIs. No framework tutorials. Just conversation.**

---

## ⏱️ Before vs After — What Changes

| Task | With Code-Based Frameworks | With MAS-Engineer |
|------|---------------------------|-------------------|
| Install + configure | 30 min reading docs + setup | `./install.sh` (10 seconds) |
| First agent | Write 20+ lines of Python | "Create me a researcher agent" |
| All agents | Classes, tasks, crews, tools | Conversation. The engineer creates them. |
| Monitoring | Hours setting up infrastructure | Included. Runs automatically. |
| Recovery from crash | Build your own retry/rollback | 5-stage system. Auto-activated. |
| Performance dashboard | Enterprise plan ($$$) | Free. Per project. MCP app. |
| Self-improvement | Not possible. Framework doesn't know itself. | 8-stage pipeline. Analyzes + fixes itself. |

**Time to first result: 1 workday → 1 coffee break.**

---

## ❌ What You Never Need to Touch

| **Don't Need** | **MAS-Engineer Handles It** |
|----------------|----------------------------|
| 🐍 Python knowledge | Talk naturally. It writes the YAML. |
| 📖 Framework API docs | 48 agents already know their jobs. |
| 🔧 Editing config files | Conversation → automatic generation. |
| 📊 Dashboard setup | One command. Per project. Forever. |
| 🔄 CI/CD for agents | Auto-commit, auto-checkpoint, auto-improve. |
| 🧪 Writing tests | Test runner + verification agent included. |
| 📚 Framework tutorials | Just talk to it. It explains itself. |

---

## 🤬 Building Multi-Agent Systems Today Sucks

You want a multi-agent system. Here's what that means today:

**1. Learn a framework** — CrewAI, LangGraph, AutoGPT. Each has its own concepts, APIs, and gotchas.

**2. Write Python code** — Agent classes, task definitions, tool integrations, crew orchestration. Hours of coding before you see anything work.

**3. Design every agent yourself** — Roles, goals, prompts, settings, backstories. Starting from a blank file every time.

**4. Figure out monitoring** — Health checks, logging, dashboards, alerts. None of the frameworks ship this — you build it.

**5. Build recovery yourself** — Retry logic, checkpointing, rollbacks, fallbacks. One crash and you're debugging.

**6. Accept your system stays static** — It never improves. Never learns from its own sessions. Never optimizes its own agents. What you built on day one is what it does forever.

**Days of work. For a system that never gets better.**

---

## 🦆 Enter MAS-Engineer

The same result. **Done through conversation.**

```
┌─ You ─────────────────────────────────────────┐
│                                                │
│   "Create a customer support agent system"      │
│                                                │
├─ MAS-Engineer ─────────────────────────────────┤
│                                                │
│   ✅ Project initialized. Base agent created.  │
│   💡 Should I research current techniques?     │
│                                                │
├─ You ─────────────────────────────────────────┤
│                                                │
│   "Yes, search for best practices"              │
│                                                │
├─ MAS-Engineer ─────────────────────────────────┤
│   🔍 Web research complete. 3 findings:        │
│     • Multi-agent patterns (high relevance)     │
│     • Recent LLM capabilities (medium)          │
│     • Security best practices (high)            │
│   What should I integrate?                     │
│                                                │
├─ You ─────────────────────────────────────────┤
│                                                │
│   "Add a researcher agent that searches the web"│
│                                                │
├─ MAS-Engineer ─────────────────────────────────┤
│                                                │
│   ✅ Agent 'researcher' created.               │
│   ✅ Registered in workflows.yaml.             │
│   ✅ Added to sub_recipes.                     │
│   ✅ SOT entry created.                        │
│                                                │
├─ You ─────────────────────────────────────────┤
│                                                │
│   "Add a writer agent for responses"            │
│                                                │
├─ MAS-Engineer ─────────────────────────────────┤
│                                                │
│   ✅ Agent 'writer' created and registered.    │
│                                                │
├─ You ─────────────────────────────────────────┤
│                                                │
│   "Set up the dashboard"                       │
│                                                │
├─ MAS-Engineer ─────────────────────────────────┤
│                                                │
│   📊 Dashboard active. Auto-refreshes every    │
│      5 minutes. Health, agents, changes visible.│
│                                                │
├─ You ─────────────────────────────────────────┤
│                                                │
│   "Improve my agents' performance"              │
│                                                │
├─ MAS-Engineer ─────────────────────────────────┤
│                                                │
│   🔄 8-stage improvement pipeline running...   │
│   ✅ 3 patches applied.                        │
│   ✅ Prompt score: 6.2 → 8.1/10               │
│   ✅ Guardian: no new drifts detected          │
│                                                │
└────────────────────────────────────────────────┘

**Time invested: a few minutes of conversation.**
**48 agents did the work behind the scenes.**
```

<p align="center">
  <b>Zero code. Zero configuration. Zero framework tutorials.</b><br>
  <i>From idea to running multi-agent system in the time it takes to have a coffee.</i>
</p>

---

## 🎁 What MAS-Engineer Ships

<p align="center">
  <table>
    <tr>
      <td align="center"><h2>🛡️</h2><b>48</b><br>Ready-to-Use<br>Sub-Agents</td>
      <td align="center"><h2>🔧</h2><b>50</b><br>Python/Shell<br>Tools</td>
      <td align="center"><h2>🔄</h2><b>8</b><br>Stage Self-<br>Improvement</td>
      <td align="center"><h2>🏥</h2><b>5</b><br>Stage<br>Recovery</td>
      <td align="center"><h2>📊</h2><b>Free</b><br>Dashboard<br>Per Project</td>
      <td align="center"><h2>📜</h2><b>23</b><br>Enforced<br>Rules</td>
    </tr>
  </table>
</p>

---

## 🆚 Why MAS-Engineer Exists

**Because building a multi-agent system shouldn't require a software engineering degree.**

| | **Code-Based Frameworks** (CrewAI, AutoGPT, LangGraph) | **MAS-Engineer** |
|---|---|---|
| **How you build agents** | 🐍 Python: `Agent(role=..., goal=...)` | 🗣️ "Create me a researcher agent" |
| **Agents out of the box** | **0** — you build everything | **48** — production-ready |
| **Self-improvement** | ❌ Your system stays the same forever | ✅ Analyzes itself, improves its agents |
| **Recovery from failure** | `max_retry_limit=2` | ✅ 5 stages: Immune→Checkpoint→Safezone→Timeline→Defib |
| **Per-project dashboard** | Enterprise plan 💰 | ✅ Free, auto-refreshing, every project |
| **Enforced governance** | Manual coding of guardrails | ✅ 11-article Constitution + 23 enforced Rules |
| **Framework generator** | ❌ | ✅ `--bootstrap` → standalone system in one command |
| **Who it's for** | Python developers who love APIs | **Anyone who needs an agent system** |

---

## 🆚 Head-to-Head with the Market

| | **MAS-Engineer** | CrewAI | MetaGPT | AutoGPT | LangGraph |
|---|---|---|---|---|---|
| **Natural Language Interface** | ✅ Core design | ❌ | ✅ CLI only | ❌ | ❌ |
| **Pre-built Agents** | **48** | 0 | 5 roles | 0 (builder) | 0 |
| **Self-Improvement** | ✅ 8-stage pipeline | ❌ | ❌ | ❌ | ❌ |
| **Recovery System** | ✅ 5 stages | ❌ | ❌ | ❌ | ❌ |
| **Framework Bootstrap** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Dashboard per System** | ✅ Free MCP app | 💰 AMP | ❌ | Built-in | LangSmith |
| **Constitution + Rules** | ✅ 11 art. + 23 rules | Guardrails | ❌ | ❌ | ❌ |
| **Install** | `./install.sh` | `pip install` | `pip install` | Docker | `pip install` |
| **GitHub Stars** | ⭐ (you decide) | 54k | 69k | 185k | 36k |

---

## 🧠 How It Works

```
                   ┌──────────────────────────────┐
                   │        YOU                    │
                   │  Natural Language Request     │
                   └──────────────┬───────────────┘
                                  │ delegates (R18)
              ┌───────────────────┼───────────────────┐
              │                   │                    │
     ┌────────▼──────┐    ┌──────▼────────┐   ┌──────▼────────┐
     │ Framework     │    │ Improvement   │   │ Monitoring    │
     │ Builders      │    │ Pipeline      │   │ & Recovery    │
     │ (8 agents)    │    │ (7 agents)    │   │ (12 agents)   │
     └───────────────┘    └───────────────┘   └───────────────┘
     ┌───────────────┐    ┌───────────────┐   ┌───────────────┐
     │ Utility       │    │ Analysis      │   │ Management    │
     │ (10 agents)   │    │ (7 agents)    │   │ (4 agents)    │
     └───────────────┘    └───────────────┘   └───────────────┘

                                     ┌──────────────────────┐
                                     │   50 Python/Shell    │
                                     │   Tools              │
                                     └──────────────────────┘
```

---

## 🧩 Where MAS-Engineer Fits in Your Stack

```
┌──────────────────────────────────────────────────────┐
│              YOUR MULTI-AGENT SYSTEM                  │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐          │
│  │Researcher │ │  Writer   │ │ Reviewer  │   ...    │
│  └───────────┘ └───────────┘ └───────────┘          │
├──────────────────────────────────────────────────────┤
│                 MAS-ENGINEER                          │
│      Builds · Improves · Monitors · Recovers         │
│      Natural language interface · 48 sub-agents      │
├──────────────────────────────────────────────────────┤
│                   GOOSE                               │
│      MCP agent platform (runtime)                    │
│      Provider-agnostic (OpenAI, Anthropic, Ollama)   │
├──────────────────────────────────────────────────────┤
│              YOUR LLM PROVIDER                        │
│      OpenAI · Anthropic · Ollama · Groq · etc.       │
└──────────────────────────────────────────────────────┘
```

MAS-Engineer sits between your LLM provider and your multi-agent system. Goose handles runtime. MAS-Engineer handles **creation, optimization, monitoring, and recovery** through natural language.

---

## 🔄 Three Operating Modes

| Mode | What the Engineer Does |
|------|-----------------------|
| 🔧 **MAS Mode** | **Improves itself** — analyzes its own sessions, finds optimization potential, patches its own agents. The framework evolves autonomously. |
| 🟢 **Framework Mode** | **Works on YOUR system** — scans for issues, patches problems, hardens security, monitors health. Your multi-agent system, maintained by AI. |
| 📁 **Generic Mode** | **Creates NEW projects** — initializes, generates agents, sets up monitoring infrastructure. A complete multi-agent system from scratch. |

One tool. Three completely different jobs. All through natural language.

---

## ⚡ Quick Start

```bash
# 1. Clone or unzip
git clone <repo> && cd mas-engineer

# 2. Install into Goose (your MCP agent platform)
./install.sh

# 3. Start Goose
goose run --recipe dev-mas-engineer

# 4. Start talking
# → "What can you do?"
# → "Create a new multi-agent system"
# → "Add a researcher agent"
# → "Set up the dashboard"
```

---

## 🎁 What's Included

| | Feature | What It Does |
|---|---|---|
| 🛡️ | **48 Sub-Agents** | Monitoring, Recovery, Improvement, Analysis, Management, Documentation, Utilities — all YAML-defines, all tested, all ready |
| 🔄 | **8-Stage Self-Improvement** | IM pipeline: Read sessions → Detect issues (53 types) → Rank → Design patches → Apply → Validate → Push improvements |
| 🏥 | **5-Stage Phoenix Recovery** | Immune (prevention) → Checkpoint (snapshots) → Safezone (isolated fork) → Timeline (best-point search) → Defib (emergency minimal config) |
| 📊 | **Per-Project Dashboard** | MCP app with health status, agent list, change history, performance metrics. Auto-refreshes every 5 minutes. Free. |
| 📜 | **Constitution + Rules** | 11 articles governing ALL agents + 23 enforced rules with hardness levels (R01-R23) |
| 🚀 | **Bootstrap Deployment** | `--bootstrap` creates a standalone MAS-Engineer distribution. All 48 agents + 50 tools + dashboard + recovery. Installable anywhere. |
| 🔍 | **Web Research** | Before creating or improving, searches goose-docs.ai, GitHub, and PyPI for current best practices |
| 🤝 | **R18 Delegation** | If a sub-agent can handle the task, the Engineer MUST delegate. No re-inventing wheels. |
| 📝 | **Auto-Documentation** | Every change logged to `changes.json`. Every operation auto-committed to git. Every session analyzed for improvement. |

---

## 💼 Who Is This For?

| Use Case | How MAS-Engineer Helps |
|----------|------------------------|
| 🏢 **Enterprise** | Deploy internal agent systems for HR, support, analytics, code review — without a dedicated AI engineering team |
| 🧪 **Research** | Start from 48 working agents. Experiment with self-improving architectures. Measure before/after scores. Publish. |
| 🚀 **Startups** | Prototype AI agent products in minutes. Deploy standalone via `--bootstrap`. Iterate by conversation, not code commits. |
| 🎓 **Education** | Learn multi-agent systems by seeing 48 real, working implementations. Understand delegation, recovery, governance through practice. |

---

## 🧠 The Philosophy

MAS-Engineer is built on five beliefs:

1. **Agents should be created by conversation, not configuration.** Natural language is the most intuitive interface.

2. **Systems should improve themselves.** If a framework can analyze its own sessions and optimize its own agents, it should.

3. **Recovery should be automatic, not manual.** Five stages of protection ensure you never lose work.

4. **48 well-designed agents are better than an empty SDK.** You shouldn't start from zero. You should start from a complete, working system.

5. **Rules should be enforced, not suggested.** If a rule matters, it should be enforced at runtime — not written in a best-practices document.

---

## 📚 Documentation

| Document | What It Covers |
|----------|---------------|
| [Documentation Index](docs/index.md) | All docs at a glance |
| [Installation & Setup](docs/installation.md) | Install, configure, update, uninstall |
| [Architecture Overview](docs/architecture.md) | Agent hierarchy, communication protocol, SOT, rules, tools |
| [Usage Guide](docs/usage.md) | Create, improve, monitor, repair, migrate, deploy |
| [Agent Catalog](docs/agents.md) | All 48 sub-agents with tasks and delegation relationships |
| [Improvement Pipeline](docs/improvement-pipeline.md) | The 8-stage self-improvement system |
| [Recovery System](docs/recovery-system.md) | 5-stage Phoenix recovery in detail |
| [Dashboard Setup](docs/dashboard.md) | Per-project MCP dashboard installation |

---

---

## ❓ FAQ

**Q: Why not just use CrewAI?**  
A: CrewAI is a Python SDK. You write code. MAS-Engineer is a conversational assistant. You talk. If you love coding and want full API control, CrewAI is great. If you want results without coding, MAS-Engineer is the only option that works this way.

**Q: Is this production-ready?**  
A: Yes. 48 agents, 5-stage recovery, auto-commit, enforces rules, validates all YAML — built for reliability. However, MAS-Engineer runs on Goose (Anthropic's MCP framework) which is the runtime.

**Q: Can I use my own LLM?**  
A: Yes. MAS-Engineer runs on Goose, which supports OpenAI, Anthropic Claude, Ollama (local), Groq, and any OpenAI-compatible provider.

**Q: How is this different from AutoGPT?**  
A: AutoGPT is a single autonomous agent. MAS-Engineer is 48 specialized agents working together. AutoGPT executes tasks. MAS-Engineer **builds and maintains complete multi-agent systems**.

**Q: Can I extend it?**  
A: Yes. Add new sub-agents by creating YAML files. Register them in workflows.yaml. The Engineer discovers them automatically. Or talk to the Engineer: "I need a new agent that monitors database performance" — it delegates to `intention-parser` and `recipe-designer`.

**Q: How many systems can I manage?**  
A: Unlimited. Each project has its own `.mas-mode` file. You switch between them by changing modes. Each gets its own dashboard, monitoring, and improvement pipeline.

**Q: Does it work with any Goose configuration?**  
A: Yes. Standard Goose setup. Provider-agnostic. Configured via `~/.config/goose/config.yaml` as usual.

---

## 🗺️ Roadmap

| Phase | What's Coming |
|:-----:|---------------|
| ✅ **Now** | 48 agents, 50 tools, 8-stage improvement, 5-stage recovery, dashboard per project |
| 🔜 **Next** | Community agent marketplace, pre-built system templates (RAG, support, analytics), one-click deploy to cloud |
| 🎯 **Future** | Visual agent builder, multi-user collaboration, enterprise RBAC, observability integrations (Datadog, Grafana) |

---

## 🤝 Contributing

MAS-Engineer is a single-developer project with an ambitious vision. Contributions welcome:

- **Found a bug?** Open an issue
- **Want a feature?** Start a discussion
- **Want to contribute code?** Fork and submit a PR

---

## 📄 License

MAS-Engineer is released under the **GNU Affero General Public License v3.0** (AGPL-3.0).

---

<p align="center">
  <br>
  <h2 align="center">Ready to stop coding agents and start talking to them?</h2>
  <br>
  <p align="center">
    <code>git clone &lt;repo&gt; && cd mas-engineer && ./install.sh && goose run --recipe dev-mas-engineer</code>
  </p>
  <p align="center">
    <b>48 agents are waiting. What do you want to build?</b>
  </p>
  <br>
</p>
