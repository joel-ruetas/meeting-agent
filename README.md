# Meeting Intelligence Agent
### Kaggle 5-Day AI Agents Capstone — Concierge Agents Track

An AI agent that transforms raw meeting transcripts into structured summaries,
prioritized action items, and calendar reminder files — with security and
human approval built in at every step.

---

## The Problem

Every meeting produces commitments that get forgotten. Someone promises to send
a report by Friday. Someone else agrees to book a room. Within 24 hours, at
least one of those things is lost. This agent solves that by turning any meeting
transcript into a structured, actionable output in seconds.

---

## What It Does

1. Reads a plain-text meeting transcript
2. Scrubs PII (emails, phone numbers, SSNs) before any AI processing
3. Checks for prompt injection attacks
4. Extracts action items with owner, task, deadline, and priority
5. Analyzes meeting tone and collaboration score
6. Writes a formatted summary with priority-sorted action tables
7. Asks a human to approve before saving anything (Human-in-the-Loop gate)
8. Saves a `.txt` summary and `.ics` calendar file to the `outputs/` folder

---

## Agent Concepts Demonstrated

| Concept | Implementation |
|---------|----------------|
| **Multi-agent system (ADK 2.0)** | Orchestrator → Structure Agent → Sentiment Agent → Action Extractor → Summary Writer |
| **MCP Server** | Custom FastMCP server for sandboxed file I/O |
| **Security features** | PII scrubber + prompt injection detection + Human-in-the-Loop approval gate |
| **Agent Skill** | `SKILL.md` loaded on demand — no context bloat |
| **Gemini + Claude** | One line in `.env` switches AI models |

---

## Architecture

```
Your Transcript
      │
      ▼
┌─────────────────┐
│  Security Node  │  Python only — zero LLM cost
│  PII scrub +    │  Blocks bad input before
│  injection det. │  it reaches any AI model
└────────┬────────┘
         │ SAFE
         ▼
┌─────────────────┐
│ Structure Agent │  Extracts date, people, topics
└────────┬────────┘
         ▼
┌─────────────────┐
│ Sentiment Agent │  Reads meeting tone and energy
└────────┬────────┘
         ▼
┌─────────────────┐
│  Action Agent   │  Finds tasks, owners, priorities
└────────┬────────┘
         ▼
┌─────────────────┐
│  Summary Agent  │  Writes final report + .ics file
└────────┬────────┘
         ▼
┌─────────────────┐
│ Human Approval  │  YOU must approve before saving
│ Gate (HITL)     │  Nothing saved without consent
└────────┬────────┘
         │ APPROVED
         ▼
┌─────────────────┐
│   MCP Server    │  Saves files via FastMCP protocol
│   File Output   │  Restricted to outputs/ folder
└─────────────────┘
```

---

## Security Design

Three layers of protection:

**Layer 1 — Before AI:** PII scrubber removes emails, phone numbers, and SSNs.
Prompt injection detector blocks malicious transcripts before any LLM call.

**Layer 2 — During AI:** Each agent is scoped to one specific task only.
No agent has access to the filesystem or internet directly.

**Layer 3 — After AI:** Human must click Approve (web UI) or type `approve`
(terminal) before any file is written to disk. Nothing is automatic.

---

## Project Structure

```
meeting-agent/
├── README.md                          ← this file
├── run.py                             ← terminal runner
├── web_app.py                         ← Streamlit web UI
├── .env.example                       ← template (copy to .env and add keys)
├── .gitignore                         ← keeps secrets out of GitHub
├── app/
│   ├── agent.py                       ← ADK multi-agent workflow
│   └── security.py                    ← PII scrubber + injection detector
├── mcp_server/
│   └── filesystem_server.py           ← FastMCP file I/O server
├── transcripts/
│   └── sample_meeting.txt             ← sample transcript for testing
├── outputs/                           ← generated summaries and .ics files
│   └── eval_report.json               ← evaluation test results
├── tests/
│   └── eval.py                        ← 90-test evaluation suite
└── .agents/
    ├── AGENTS.md                      ← agent rules and conventions
    └── skills/
        └── meeting-summary/
            └── SKILL.md               ← agent skill loaded on demand
```

---

## Setup

### Prerequisites
- Python 3.11 or newer
- A Gemini API key — free at [aistudio.google.com](https://aistudio.google.com)
- Optional: An Anthropic API key for Claude — [console.anthropic.com](https://console.anthropic.com)

### Install

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/meeting-agent.git
cd meeting-agent

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux

# Install dependencies
pip install google-adk mcp python-dotenv litellm streamlit pandas google-generativeai
```

### Configure

Copy `.env.example` to `.env` and add your API key:

```
GEMINI_API_KEY=your_gemini_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here_optional
MODEL_PROVIDER=gemini
```

### Run — Terminal mode (no browser)

```bash
python run.py transcripts/sample_meeting.txt
```

### Run — Web UI

```bash
streamlit run web_app.py
```

Opens at `http://localhost:8501` with dark/light mode toggle,
live security pre-check, animated pipeline progress, analytics tab,
and download buttons.

### Run — Evaluation suite

```bash
# Quick (no API calls)
python tests/eval.py --quick

# Full (calls Gemini for LLM-as-judge scoring)
python tests/eval.py
```

---

## Switching Between Gemini and Claude

Open your `.env` file and change one line:

```
MODEL_PROVIDER=gemini    # Google Gemini 2.5 Flash (free)
MODEL_PROVIDER=claude    # Anthropic Claude Sonnet 4.6 (needs API key)
```

The agent code is identical. Only the model changes.

---

## Sample Output

Given a meeting transcript, the agent produces:

**Summary file** (`outputs/sample_meeting_summary.txt`):
```
# Meeting Summary — June 27, 2026

## Attendees
Sarah Chen, Marcus Williams, Priya Patel, Tom Rodriguez

## Meeting Tone
😊 Positive | Energy: high | Collaboration: 8/10

## Action Items by Priority

### 🔴 High Priority
| Owner | Task | Due Date | Category |
|-------|------|----------|----------|
| Tom | Update dashboard with new metrics | Monday | deliverable |

### 🟡 Medium Priority
| Owner | Task | Due Date | Category |
|-------|------|----------|----------|
| Marcus | Share Q3 roadmap draft | Friday | deliverable |
```

**Calendar file** (`outputs/sample_meeting.ics`) — importable into any
calendar app (Google Calendar, Outlook, Apple Calendar).

---

## Evaluation Results

The project includes a 90-test evaluation suite covering:
- PII scrubbing (10 tests)
- Prompt injection detection (10 tests)
- ICS calendar file validation (11 tests)
- Meeting summary format validation (15 tests)
- MCP file safety and path traversal (7 tests)
- Security edge cases (10 tests)
- Environment and configuration checks (12 tests)
- LLM integration with LLM-as-judge scoring (7 tests)
- Regression tests for edge cases (8 tests)

**Score: 100% passing (quick mode) / 93%+ with LLM tests**

---

## Design Decisions

**Why a multi-agent graph instead of one large prompt?**
Each specialist agent has a smaller context window and a narrower set of
instructions. This reduces hallucination, makes each step auditable, and
allows individual agents to be swapped or improved without touching the others.

**Why FastMCP for file I/O?**
Using MCP instead of direct file access means the agent never touches the
filesystem directly. The MCP server enforces a hard boundary: reads only from
`transcripts/`, writes only to `outputs/`. Path traversal attacks are blocked
by design.

**Why Human-in-the-Loop?**
An agent that saves files automatically without review is a security risk.
The HITL gate ensures a human reads the output before it is persisted.
This is especially important for meeting notes which may contain sensitive
business information.

**Why separate security from the LLM pipeline?**
The PII scrubber and injection detector are pure Python — no AI involved.
This means they are deterministic, fast, auditable, and cannot be
manipulated by clever prompt wording in the transcript.

---

## Tracks and Criteria

**Track:** Concierge Agents
**Problem:** Meeting action items get forgotten
**Solution:** AI agent pipeline with security, HITL, and structured output
**Value:** Saves time, reduces missed commitments, keeps data private

---

## License

MIT License — see LICENSE file for details.

---

## Author

Built for the Kaggle 5-Day AI Agents Intensive Capstone, June 2026.
