"""CLI entry point for the Meeting Intelligence Agent pipeline.

This script validates input, applies security checks, runs transcript
processing, and saves approved summary and calendar outputs.
"""

# Local run command:
# python run.py transcripts/your_meeting.txt

import sys
import asyncio
import pathlib
import os
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from app.security import scrub_pii, check_prompt_injection


async def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py transcripts/your_meeting.txt")
        sys.exit(1)

    filepath = pathlib.Path(sys.argv[1])
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    transcript_text = filepath.read_text(encoding="utf-8")
    filename = filepath.name

    print(f"\nProcessing: {filename}")
    print("-" * 50)

    # Step 1: Security check
    print("Step 1: Running security check...")
    if check_prompt_injection(transcript_text):
        print("BLOCKED: Suspicious instructions detected.")
        sys.exit(1)

    clean_text, redacted = scrub_pii(transcript_text)
    if redacted:
        print(f"Security: Redacted {len(redacted)} PII item(s).")
    else:
        print("Security: No PII detected.")

    # Step 2: Run the agent
    print("Step 2: Running agent pipeline...")
    print("-" * 50)

    full_response = await run_with_adk(clean_text, filename)

    if not full_response:
        print("ADK runner failed, trying direct Gemini API...")
        full_response = await direct_gemini_call(clean_text)

    if not full_response:
        print("No response received. Check your API key in .env")
        sys.exit(1)

    # Step 3: Parse the response
    if "---ICS_START---" in full_response:
        parts = full_response.split("---ICS_START---", 1)
        summary_text = parts[0].strip()
        calendar_text = parts[1].strip()
    else:
        summary_text = full_response.strip()
        calendar_text = generate_basic_ics()

    # Step 4: Human approval gate
    print("\n" + "=" * 60)
    print("MEETING SUMMARY — PLEASE REVIEW BEFORE SAVING")
    print("=" * 60)
    print(summary_text)
    print("=" * 60)

    if redacted:
        print(f"\nNote: {len(redacted)} PII item(s) were redacted.")

    response = input("\nType 'approve' to save, or anything else to cancel: ")

    if response.strip().lower() != "approve":
        print("\nCancelled. No files were saved.")
        sys.exit(0)

    # Step 5: Save files
    outputs = pathlib.Path("outputs")
    outputs.mkdir(exist_ok=True)

    base_name = filename.replace(".txt", "").replace(".md", "")
    summary_path = outputs / f"{base_name}_summary.txt"
    calendar_path = outputs / f"{base_name}.ics"

    summary_path.write_text(summary_text, encoding="utf-8")
    calendar_path.write_text(calendar_text, encoding="utf-8")

    print(f"\nSaved summary:  {summary_path}")
    print(f"Saved calendar: {calendar_path}")
    print("\nDone! Open the .ics file in any calendar app to import reminders.")


async def run_with_adk(clean_text: str, filename: str) -> str:
    """Runs the agent using the ADK runner."""
    try:
        from google.adk.runners import InMemoryRunner
        from google.genai import types
        from app.agent import app as agent_app

        runner = InMemoryRunner(
            agent=agent_app,
            app_name="meeting_intelligence_agent"
        )
        session = await runner.session_service.create_session(
            app_name="meeting_intelligence_agent",
            user_id="user",
        )

        prompt = f"Please process this meeting transcript:\n\n{clean_text}"

        message = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )

        # Collect text per author. In the multi-agent pipeline only the final
        # summary_agent output is the deliverable — the structure/sentiment/
        # action agents emit intermediate JSON we don't want in the summary.
        by_author = {}
        async for event in runner.run_async(
            user_id="user",
            session_id=session.id,
            new_message=message
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        author = event.author or "agent"
                        by_author[author] = by_author.get(author, "") + part.text

        if "summary_agent" in by_author:
            return by_author["summary_agent"]
        return "".join(by_author.values())

    except Exception as e:
        print(f"ADK runner error: {e}")
        return ""


async def direct_gemini_call(transcript_text: str) -> str:
    """Fallback: calls Gemini directly without ADK."""
    try:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("No GEMINI_API_KEY in .env file")
            return ""

        client = genai.Client(api_key=api_key)

        from app.agent import FULL_INSTRUCTION
        prompt = f"{FULL_INSTRUCTION}\n\nTRANSCRIPT:\n{transcript_text}"

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text

    except Exception as e:
        print(f"Direct Gemini call failed: {e}")
        return ""


def generate_basic_ics() -> str:
    """Generates a minimal .ics file as fallback."""
    from datetime import datetime, timedelta
    next_week = datetime.now() + timedelta(days=7)
    date_str = next_week.strftime("%Y%m%d")
    return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Meeting Agent//EN
BEGIN:VEVENT
DTSTART;VALUE=DATE:{date_str}
DTEND;VALUE=DATE:{date_str}
SUMMARY:Review meeting action items
DESCRIPTION:Check the meeting summary file for all action items.
END:VEVENT
END:VCALENDAR"""


if __name__ == "__main__":
    asyncio.run(main())