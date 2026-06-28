# Meeting Intelligence Agent — Rules

## Core principles
- Always run the security checkpoint before any transcript reaches an LLM.
- Never save files without explicit human approval.
- Never add action items that are not stated in the transcript.
- Never include PII in the output even if it appeared in the input.

## Code style
- Keep each agent focused on one job only.
- Add print statements at each step so the human can follow along.
- Use structured JSON for passing data between agents.

## What this agent does NOT do
- It does not send emails.
- It does not access the internet.
- It does not modify files outside the outputs/ folder.