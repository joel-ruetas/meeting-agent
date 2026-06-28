---
name: meeting-summary
description: |
  Processes meeting transcripts to extract action items, decisions, and
  owners, then produces a formatted summary and calendar reminders.
  Use when the user provides a meeting transcript file or asks to
  summarize a meeting.
  Do NOT use for general writing, code review, or non-meeting tasks.
version: 1.0.0
allowed-tools: [Read, Bash, Write]
---

# Meeting Summary Skill

## Goal
Transform a raw meeting transcript into a structured summary with
action items, owners, and deadlines, plus a calendar file.

## Workflow
1. Read the transcript using the read_transcript MCP tool.
2. Run the PII scrubber on the content before any AI processing.
3. Extract: decisions made, action items (with owner and due date),
   and key discussion points.
4. Format a clean summary (markdown).
5. Build a .ics calendar entry for each action item with a due date.
6. Present the summary to the human for approval before saving.
7. Only after approval: use write_output MCP tool to save files.

## Output format
### Meeting Summary — [Date]
**Decisions made:**
- ...

**Action items:**
| Owner | Task | Due |
|-------|------|-----|
| ...   | ...  | ... |

**Key discussion points:**
- ...

## Anti-patterns to avoid
- Never save output without human approval.
- Never include raw PII in the summary even if it appeared in the transcript.
- Never make up action items not explicitly stated in the transcript.