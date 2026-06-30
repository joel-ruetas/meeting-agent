"""Agent configuration for the Meeting Intelligence pipeline.

This module wires model selection, safety preprocessing, specialist agents,
and workflow/fallback assembly used by CLI and web entry points.
"""

# Core orchestration module imported by run.py and other app integrations.

import os
import sys
import pathlib
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from app.security import scrub_pii, check_prompt_injection

# ── Model selection ───────────────────────────────────────────────────────────
_provider = os.getenv("MODEL_PROVIDER", "gemini").lower()

if _provider == "claude":
    try:
        from google.adk.models.lite_llm import LiteLlm
        MODEL = LiteLlm(model="anthropic/claude-sonnet-4-6")
        print("Using model: Claude Sonnet 4.6")
    except Exception:
        MODEL = "gemini-2.5-flash"
        print("Falling back to Gemini")
else:
    MODEL = "gemini-2.5-flash"
    print("Using model: Gemini 2.5 Flash")

# ── Try ADK multi-agent pipeline, fall back to single Agent ──────────────────
# ADK 2.x exposes SequentialAgent for orchestrating specialist sub-agents.
try:
    from google.adk.agents import Agent, SequentialAgent
    ADK_WORKFLOW = True
    print("ADK multi-agent pipeline enabled")
except ImportError:
    from google.adk.agents import Agent
    ADK_WORKFLOW = False
    print("ADK SequentialAgent not available, using single agent")

# Deterministic generation: temperature 0 keeps the agents' output stable
# across runs. This makes the summary/action-item extraction reproducible,
# which in turn keeps the LLM eval suite from flaking on sampling variance.
# temperature=0 keeps the agents' output focused and consistent in every
# context. gemini-2.5-flash's "thinking" step is non-deterministic even at
# temperature 0 and compounds across the 4-agent pipeline, so for reproducible
# evaluation we additionally disable it — but ONLY when MEETING_AGENT_DETERMINISTIC
# is set (the eval suite sets it). Normal production runs keep thinking on for
# richer output.
_DETERMINISTIC = os.getenv("MEETING_AGENT_DETERMINISTIC", "").lower() in (
    "1", "true", "yes", "on"
)
try:
    from google.genai import types
    if _DETERMINISTIC:
        try:
            GEN_CONFIG = types.GenerateContentConfig(
                temperature=0.0,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            )
        except Exception:
            # Older SDK without ThinkingConfig — fall back to temperature only.
            GEN_CONFIG = types.GenerateContentConfig(temperature=0.0)
    else:
        GEN_CONFIG = types.GenerateContentConfig(temperature=0.0)
except Exception:
    GEN_CONFIG = None

# ── Security node (pure Python, zero LLM cost) ───────────────────────────────
def security_node(transcript: str) -> dict:
    """
    Runs before any LLM call.
    Scrubs PII and checks for prompt injection.
    Returns a route: 'safe' or 'blocked'
    """
    if check_prompt_injection(transcript):
        return {"route": "blocked", "clean_text": "", "redacted": []}

    clean_text, redacted = scrub_pii(transcript)
    return {
        "route": "safe",
        "clean_text": clean_text,
        "redacted": redacted
    }


# ── Specialist agents ─────────────────────────────────────────────────────────

structure_agent = Agent(
    name="structure_agent",
    model=MODEL,
    generate_content_config=GEN_CONFIG,
    instruction="""You extract the structure of a meeting transcript.
    
    Return a JSON object with exactly these keys:
    - date: meeting date as string (or "Date unknown")
    - participants: list of participant names
    - topics: list of main discussion topics (brief phrases)
    
    Be concise. Extract only what is stated. Do not add information.""",
)

sentiment_agent = Agent(
    name="sentiment_agent",
    model=MODEL,
    generate_content_config=GEN_CONFIG,
    instruction="""You analyze the tone and sentiment of a meeting transcript.
    
    Return a JSON object with exactly these keys:
    - overall_tone: one of "positive", "neutral", "tense", "mixed"
    - energy_level: one of "high", "medium", "low"
    - collaboration_score: integer 1-10 (10 = highly collaborative)
    - key_observation: one sentence about the meeting dynamics
    
    Base your analysis only on the language and interactions in the transcript.""",
)

action_agent = Agent(
    name="action_agent",
    model=MODEL,
    generate_content_config=GEN_CONFIG,
    instruction="""You extract action items from a meeting transcript.
    
    For each action item return a JSON array where each item has:
    - owner: who will do it (use "Unknown" if not clear)
    - task: what they will do (one clear verb-led sentence)
    - due_date: deadline mentioned (use "No date set" if not mentioned)  
    - priority: "HIGH", "MEDIUM", or "LOW" based on urgency language used
    - category: one of "deliverable", "meeting", "review", "communication", "other"
    
    Rules:
    - Only include genuine commitments people made
    - Never invent items not stated in the transcript
    - HIGH priority = words like "urgent", "ASAP", "critical", "today", "tomorrow"
    - LOW priority = words like "eventually", "when you get a chance", "sometime"
    - Everything else = MEDIUM priority""",
)

summary_agent = Agent(
    name="summary_agent",
    model=MODEL,
    generate_content_config=GEN_CONFIG,
    instruction="""You write a professional meeting summary.

    You receive structured data about a meeting. Write a summary in this format:

# Meeting Summary — [date]

## Attendees
[participants as comma-separated list]

## Meeting Tone
[tone emoji] [overall_tone] | Energy: [energy_level] | Collaboration: [score]/10
[key_observation]

## Key Discussion Points
[topics as bullet list]

## Action Items by Priority

### 🔴 High Priority
| Owner | Task | Due Date | Category |
|-------|------|----------|----------|
[high priority rows, or "None" if empty]

### 🟡 Medium Priority
| Owner | Task | Due Date | Category |
|-------|------|----------|----------|
[medium priority rows]

### 🟢 Low Priority
| Owner | Task | Due Date | Category |
|-------|------|----------|----------|
[low priority rows]

## Next Steps
[one sentence about what should happen immediately after this meeting]

---
*Generated by Meeting Intelligence Agent | [count] action items identified*

Then write ---ICS_START--- on its own line, followed by a complete .ics file
with one VEVENT per action item. Use YYYYMMDD date format.
HIGH priority items get a PRIORITY:1 property.
MEDIUM items get PRIORITY:5.
LOW items get PRIORITY:9.

IMPORTANT RULES:
- Never include emails, phone numbers, or SSNs
- Use tone emojis: positive=😊 neutral=😐 tense=😤 mixed=🤔
- Always include ---ICS_START--- separator""",
)


# ── Single-agent instruction ─────────────────────────────────────────────────
# Defined unconditionally so the direct-Gemini fallback (in run.py / web_app.py /
# tests) can import it regardless of which app variant is built below.
FULL_INSTRUCTION = """You are the Meeting Intelligence Agent.

When given a meeting transcript, you must do ALL of these steps in order:

STEP 1 - ANALYZE STRUCTURE:
Extract date, participants, and main topics.

STEP 2 - ANALYZE SENTIMENT:
Determine overall_tone (positive/neutral/tense/mixed),
energy_level (high/medium/low), collaboration_score (1-10),
and one key_observation sentence.

STEP 3 - EXTRACT ACTION ITEMS:
Find every commitment with owner, task, due_date, priority (HIGH/MEDIUM/LOW),
and category (deliverable/meeting/review/communication/other).
HIGH = urgent/ASAP/today. LOW = eventually/sometime. Rest = MEDIUM.

STEP 4 - WRITE THE SUMMARY in this exact format:

# Meeting Summary — [DATE]

## Attendees
[names]

## Meeting Tone
[emoji] [tone] | Energy: [level] | Collaboration: [score]/10
[observation]

## Key Discussion Points
- [topics]

## Action Items by Priority

### 🔴 High Priority
| Owner | Task | Due Date | Category |
|-------|------|----------|----------|
[rows or "None"]

### 🟡 Medium Priority
| Owner | Task | Due Date | Category |
[rows]

### 🟢 Low Priority
| Owner | Task | Due Date | Category |
[rows]

## Next Steps
[one sentence]

---
*Generated by Meeting Intelligence Agent | [N] action items identified*

Then write ---ICS_START--- on its own line followed by a .ics calendar file.
One VEVENT per action item. Date format YYYYMMDD.
HIGH=PRIORITY:1, MEDIUM=PRIORITY:5, LOW=PRIORITY:9.

RULES: No emails/phones/SSNs. No invented items. Always include ---ICS_START---."""


# ── Build the agent app ───────────────────────────────────────────────────────

if ADK_WORKFLOW:
    # Multi-agent pipeline — the four specialists run in sequence and each
    # sees the prior agents' output in the shared session:
    #   structure → sentiment → action extraction → final summary
    try:
        app = SequentialAgent(
            name="meeting_intelligence_workflow",
            sub_agents=[
                structure_agent,
                sentiment_agent,
                action_agent,
                summary_agent,
            ],
        )
        print("Multi-agent pipeline created successfully")
    except Exception as e:
        print(f"Pipeline creation issue: {e}, using single agent")
        ADK_WORKFLOW = False

if not ADK_WORKFLOW:
    # Fallback: single powerful agent with everything in the prompt
    app = Agent(
        name="meeting_intelligence_agent",
        model=MODEL,
        generate_content_config=GEN_CONFIG,
        instruction=FULL_INSTRUCTION,
    )