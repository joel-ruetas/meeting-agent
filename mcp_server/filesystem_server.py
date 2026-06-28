"""Filesystem MCP server for transcript input and output artifacts.

This module exposes constrained tools to read transcript files and write
approved summary/calendar outputs within project-controlled directories.
"""

# Local run command:
# python mcp_server/filesystem_server.py

from mcp.server.fastmcp import FastMCP
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Create the MCP server with a name
mcp = FastMCP("Meeting Filesystem Server")


@mcp.tool()
def read_transcript(filename: str) -> str:
    """
    Reads a meeting transcript from the transcripts folder.
    Only files inside the transcripts/ folder can be read (security boundary).
    """
    filepath = TRANSCRIPTS_DIR / Path(filename).name
    if not filepath.exists():
        return f"Error: File '{filename}' not found in transcripts folder."
    return filepath.read_text(encoding="utf-8")


@mcp.tool()
def write_output(summary_text: str, calendar_text: str, base_filename: str) -> str:
    """
    Saves the approved meeting summary and calendar file to the outputs folder.
    Only writes to the outputs/ folder (security boundary).
    """
    OUTPUTS_DIR.mkdir(exist_ok=True)
    summary_path = OUTPUTS_DIR / f"{base_filename}_summary.txt"
    calendar_path = OUTPUTS_DIR / f"{base_filename}.ics"
    summary_path.write_text(summary_text, encoding="utf-8")
    calendar_path.write_text(calendar_text, encoding="utf-8")
    return f"Saved: {summary_path.name} and {calendar_path.name}"


if __name__ == "__main__":
    mcp.run()