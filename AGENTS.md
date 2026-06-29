# Meeting Intelligence Agent — Claude Code Instructions

## Project overview
This is a multi-agent AI pipeline built with Google ADK 2.0.
It processes meeting transcripts and extracts action items.

## Key files
- app/agent.py — the main ADK multi-agent workflow
- app/security.py — PII scrubber and injection detector
- mcp_server/filesystem_server.py — FastMCP file server
- web_app.py — Streamlit web interface
- run.py — terminal runner
- tests/eval.py — 91-test evaluation suite

## Rules Claude Code must follow
- Never hardcode API keys — always use .env
- Never modify .env
- Never write files outside outputs/ folder
- Always run tests after making changes: python tests/eval.py --quick
- Keep security.py deterministic — no LLM calls in that file
- Never remove the human approval gate from run.py or web_app.py

## Code style
- Python 3.11
- Add comments explaining WHY not just WHAT
- Keep each agent focused on one task only
- Use pathlib not os.path for file operations