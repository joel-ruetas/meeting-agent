"""Streamlit web UI for the Meeting Intelligence Agent.

This module renders an interactive interface for transcript analysis,
security checks, and summary/calendar artifact generation.
"""

# Local run command:
# streamlit run web_app.py

import streamlit as st
import asyncio
import pathlib
import os
import sys
import re
from datetime import datetime, timedelta
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

from app.security import scrub_pii, check_prompt_injection

st.set_page_config(
    page_title="Meeting Intelligence Agent",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Theme state ───────────────────────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = False

dark = st.session_state["dark_mode"]

# ── Theme tokens ──────────────────────────────────────────────────────────────
if dark:
    BG         = "#0F172A"
    SURFACE    = "#1E293B"
    BORDER     = "#334155"
    TEXT       = "#F1F5F9"
    TEXT2      = "#94A3B8"
    TEXT3      = "#475569"
    ICON_BG    = "#263548"
    CARD_SH    = "0 1px 3px rgba(0,0,0,0.4),0 4px 12px rgba(0,0,0,0.3)"
    CODE_BG    = "#020817"
else:
    BG         = "#F0F2FA"
    SURFACE    = "#FFFFFF"
    BORDER     = "#E2E8F0"
    TEXT       = "#1E293B"
    TEXT2      = "#64748B"
    TEXT3      = "#94A3B8"
    ICON_BG    = "#EEF2FF"
    CARD_SH    = "0 1px 3px rgba(0,0,0,0.06),0 4px 12px rgba(0,0,0,0.04)"
    CODE_BG    = "#0F172A"

PRIMARY = "#6366F1"
ACCENT  = "#8B5CF6"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
ERROR   = "#EF4444"
INFO    = "#3B82F6"

# ── Write config.toml ─────────────────────────────────────────────────────────
config_dir = pathlib.Path(".streamlit")
config_dir.mkdir(exist_ok=True)
(config_dir / "config.toml").write_text(f"""
[theme]
base = "{"dark" if dark else "light"}"
primaryColor = "{PRIMARY}"
backgroundColor = "{BG}"
secondaryBackgroundColor = "{SURFACE}"
textColor = "{TEXT}"

[theme.sidebar]
backgroundColor = "#0F172A"
secondaryBackgroundColor = "#1E293B"
textColor = "#CBD5E1"
primaryColor = "#818CF8"
""")

# ── Load Material Icons ───────────────────────────────────────────────────────
st.markdown(
    '<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Round" rel="stylesheet">',
    unsafe_allow_html=True
)

# ── Markdown scaling CSS (separate block — no f-string, no theme variables) ──
st.markdown("""
<style>
.stMarkdown h1 { font-size: 18px !important; font-weight: 700 !important; margin-bottom: 6px !important; margin-top: 8px !important; }
.stMarkdown h2 { font-size: 15px !important; font-weight: 600 !important; margin-bottom: 4px !important; margin-top: 12px !important; }
.stMarkdown h3 { font-size: 13px !important; font-weight: 600 !important; margin-bottom: 4px !important; margin-top: 10px !important; }
.stMarkdown p, .stMarkdown li { font-size: 13px !important; line-height: 1.6 !important; }
.stMarkdown table { font-size: 12px !important; width: 100% !important; }
.stMarkdown th { font-size: 11px !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.5px !important; padding: 6px 8px !important; }
.stMarkdown td { font-size: 12px !important; padding: 5px 8px !important; }
.stMarkdown em { font-size: 11px !important; color: #94A3B8 !important; }
</style>
""", unsafe_allow_html=True)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
#MainMenu, footer {{ visibility: hidden; }}
/* Own the base text color here — config.toml's textColor only applies at
   server start, not on rerun, so a live theme toggle must set color in CSS. */
.stApp {{ background: {BG} !important; color: {TEXT} !important; }}
/* Default text rendered by Streamlit (markdown body, plain text, widget
   content) inherits from .stApp above. Custom HTML keeps its inline colors. */
.stApp [data-testid="stText"], .stApp [data-testid="stText"] pre,
.stApp .stMarkdown, .stApp .stHeading, .stApp [data-testid="stWidgetLabel"] {{
    color: {TEXT} !important;
}}
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {PRIMARY}, {ACCENT}) !important;
    border: none !important; color: white !important;
    font-weight: 600 !important; border-radius: 8px !important;
    box-shadow: 0 4px 14px rgba(99,102,241,0.4) !important;
}}
.stButton > button[kind="primary"]:hover {{
    box-shadow: 0 6px 20px rgba(99,102,241,0.6) !important;
    transform: translateY(-1px) !important;
}}
.stButton > button:not([kind="primary"]) {{
    background: {SURFACE} !important;
    border: 1.5px solid {PRIMARY} !important;
    color: {PRIMARY} !important;
    font-weight: 600 !important; border-radius: 8px !important;
}}
.stTabs [data-baseweb="tab-list"] {{
    background: {SURFACE} !important;
    border-bottom: 2px solid {BORDER} !important; gap: 0 !important;
}}
.stTabs [data-baseweb="tab"] {{
    color: {TEXT2} !important; font-weight: 600 !important;
    font-size: 13px !important; padding: 14px 24px !important;
}}
.stTabs [aria-selected="true"] {{
    color: {PRIMARY} !important;
    border-bottom: 2px solid {PRIMARY} !important;
}}
.stProgress > div > div > div > div {{
    background: linear-gradient(90deg, {PRIMARY}, {ACCENT}) !important;
}}
.stTextArea textarea, .stTextInput input {{
    border-radius: 8px !important; border: 1.5px solid {BORDER} !important;
    background: {SURFACE} !important; color: {TEXT} !important;
}}
.stRadio label, div[data-testid="stRadio"] label {{
    color: {TEXT} !important;
}}
div[data-testid="stRadio"] div[role="radio"] + div {{
    color: {TEXT} !important;
}}
.stRadio p {{
    color: {TEXT} !important;
}}
.stCheckbox label, div[data-testid="stCheckbox"] label {{
    color: {TEXT} !important;
}}
.stSelectbox label {{
    color: {TEXT} !important;
}}
.stCaption, .stCaption p {{
    color: {TEXT2} !important;
}}
.stFileUploader label, .stFileUploader p {{
    color: {TEXT} !important;
}}
.stExpander summary p {{
    color: {TEXT} !important;
}}
.stDownloadButton button {{
    background: {SURFACE} !important;
    border: 1.5px solid {PRIMARY} !important;
    color: {PRIMARY} !important; border-radius: 8px !important;
    font-weight: 600 !important;
}}

.stMarkdown h1 {{
    font-size: 18px !important;
    font-weight: 700 !important;
    color: inherit !important;
    margin-bottom: 6px !important;
    margin-top: 8px !important;
}}
.stMarkdown h2 {{
    font-size: 15px !important;
    font-weight: 600 !important;
    color: inherit !important;
    margin-bottom: 4px !important;
    margin-top: 12px !important;
}}
.stMarkdown h3 {{
    font-size: 13px !important;
    font-weight: 600 !important;
    color: inherit !important;
    margin-bottom: 4px !important;
    margin-top: 10px !important;
}}
.stMarkdown p, .stMarkdown li {{
    font-size: 13px !important;
    line-height: 1.6 !important;
    color: inherit !important;
}}
.stMarkdown table {{
    font-size: 12px !important;
    width: 100% !important;
}}
.stMarkdown th {{
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    padding: 6px 8px !important;
}}
.stMarkdown td {{
    font-size: 12px !important;
    padding: 5px 8px !important;
}}
.stMarkdown em {{
    font-size: 11px !important;
    color: #94A3B8 !important;
}}
</style>
""", unsafe_allow_html=True)


# ── Helper functions ──────────────────────────────────────────────────────────
def mi(name, color=PRIMARY, size="20px"):
    return (f'<span class="material-icons-round" style="font-size:{size};'
            f'color:{color};vertical-align:middle;line-height:1;">{name}</span>')

def card_open(border_color=None, padding="20px 24px"):
    border = f"border-top:3px solid {border_color};" if border_color else ""
    return (f'<div style="background:{SURFACE};border-radius:12px;'
            f'box-shadow:{CARD_SH};padding:{padding};'
            f'margin-bottom:16px;{border}">')

def card_close():
    return '</div>'

def icon_row(ic, text, color=TEXT2):
    return (f'<div style="display:flex;align-items:center;gap:10px;'
            f'padding:5px 0;font-size:13px;font-weight:500;">'
            f'{mi(ic,color,"17px")}'
            f'<span style="color:{color};">{text}</span></div>')

def section_label(text):
    return (f'<div style="font-size:10px;font-weight:700;letter-spacing:2px;'
            f'text-transform:uppercase;color:{TEXT3};margin-bottom:10px;">'
            f'{text}</div>')

def metric_card(value, title, icon_name):
    return (f'<div style="background:{SURFACE};border-radius:12px;'
            f'box-shadow:{CARD_SH};padding:20px;text-align:center;'
            f'border-top:3px solid {PRIMARY};">'
            f'<div style="font-size:10px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:{TEXT3};margin-bottom:8px;">'
            f'{mi(icon_name,PRIMARY,"15px")}&nbsp;{title}</div>'
            f'<div style="font-size:40px;font-weight:300;color:{PRIMARY};">'
            f'{value}</div></div>')

def pipeline_row(ic, color, title, desc):
    return (f'<div style="display:flex;gap:14px;padding:10px 0;'
            f'border-bottom:1px solid {BORDER};">'
            f'<div style="width:34px;height:34px;border-radius:8px;'
            f'background:{ICON_BG};flex-shrink:0;display:flex;'
            f'align-items:center;justify-content:center;">'
            f'{mi(ic,color,"17px")}</div>'
            f'<div><div style="font-size:13px;font-weight:600;color:{TEXT};">'
            f'{title}</div>'
            f'<div style="font-size:12px;color:{TEXT2};margin-top:2px;">'
            f'{desc}</div></div></div>')

def security_layer_row(ic, color, title, desc):
    return (f'<div style="display:flex;gap:14px;padding:10px 0;'
            f'border-bottom:1px solid {BORDER};">'
            f'<div style="width:36px;height:36px;border-radius:50%;'
            f'background:{ICON_BG};flex-shrink:0;display:flex;'
            f'align-items:center;justify-content:center;">'
            f'{mi(ic,color,"18px")}</div>'
            f'<div><div style="font-size:13px;font-weight:600;color:{color};">'
            f'{title}</div>'
            f'<div style="font-size:12px;color:{TEXT2};margin-top:2px;">'
            f'{desc}</div></div></div>')

def concept_row(ic, title, desc):
    return (f'<tr style="border-bottom:1px solid {BORDER};">'
            f'<td style="padding:10px 8px;width:32px;">{mi(ic,PRIMARY,"17px")}</td>'
            f'<td style="padding:10px 8px;">'
            f'<div style="font-size:13px;font-weight:600;color:{TEXT};">{title}</div>'
            f'<div style="font-size:12px;color:{TEXT2};margin-top:2px;">{desc}</div>'
            f'</td></tr>')

def _basic_ics():
    d = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
    return (f"BEGIN:VCALENDAR\nVERSION:2.0\n"
            f"PRODID:-//Meeting Intelligence Agent//EN\n"
            f"BEGIN:VEVENT\nDTSTART;VALUE=DATE:{d}\n"
            f"DTEND;VALUE=DATE:{d}\n"
            f"SUMMARY:Review meeting action items\n"
            f"DESCRIPTION:Check your meeting summary.\n"
            f"PRIORITY:5\nEND:VEVENT\nEND:VCALENDAR")


# ── App bar ───────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="background:linear-gradient(135deg,#4F46E5 0%,#7C3AED 100%);'
    f'padding:18px 32px;margin-bottom:8px;border-radius:0 0 16px 16px;'
    f'box-shadow:0 4px 24px rgba(79,70,229,0.3);'
    f'display:flex;align-items:center;gap:18px;">'
    f'<div style="width:46px;height:46px;background:rgba(255,255,255,0.15);'
    f'border-radius:12px;display:flex;align-items:center;'
    f'justify-content:center;flex-shrink:0;">'
    f'{mi("psychology","white","26px")}</div>'
    f'<div style="flex:1;">'
    f'<div style="font-size:21px;font-weight:700;color:white;">'
    f'Meeting Intelligence Agent</div>'
    f'<div style="font-size:12px;color:rgba(255,255,255,0.7);margin-top:3px;">'
    f'Google ADK 2.0 &bull; MCP Server &bull; '
    f'Multi-agent pipeline &bull; Security-first</div></div>'
    f'<div style="background:rgba(255,255,255,0.15);'
    f'border:1px solid rgba(255,255,255,0.25);border-radius:99px;'
    f'padding:5px 16px;font-size:12px;font-weight:600;color:white;">'
    f'Concierge Track</div></div>',
    unsafe_allow_html=True
)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f'<div style="padding:8px 4px 16px;">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">'
        f'{mi("psychology","#818CF8","20px")}'
        f'<span style="font-size:15px;font-weight:700;">MIA</span></div>'
        f'<div style="font-size:11px;color:#94A3B8;">Meeting Intelligence Agent</div>'
        f'</div>'
        f'<hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);'
        f'margin:0 0 16px;">',
        unsafe_allow_html=True
    )

    # Appearance toggle
    st.markdown(
        f'<div style="font-size:10px;font-weight:700;letter-spacing:2px;'
        f'text-transform:uppercase;color:#64748B;margin-bottom:10px;">'
        f'Appearance</div>',
        unsafe_allow_html=True
    )
    col_l, col_d = st.columns(2)
    with col_l:
        if st.button(
            "✓ Light" if not dark else "Light",
            use_container_width=True, key="light_btn"
        ):
            st.session_state["dark_mode"] = False
            st.rerun()
    with col_d:
        if st.button(
            "✓ Dark" if dark else "Dark",
            use_container_width=True, key="dark_btn"
        ):
            st.session_state["dark_mode"] = True
            st.rerun()

    st.markdown(
        f'<hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);'
        f'margin:16px 0;">'
        f'<div style="font-size:10px;font-weight:700;letter-spacing:2px;'
        f'text-transform:uppercase;color:#64748B;margin-bottom:10px;">'
        f'Model</div>',
        unsafe_allow_html=True
    )

    model_choice = st.selectbox(
        "Model",
        ["Gemini 2.5 Flash (Free)", "Claude Sonnet 4.6"],
        label_visibility="collapsed"
    )
    os.environ["MODEL_PROVIDER"] = "claude" if "Claude" in model_choice else "gemini"
    model_name = "Gemini 2.5 Flash" if "Gemini" in model_choice else "Claude Sonnet 4.6"

    st.markdown(
        f'<div style="margin:8px 0 20px;padding:10px 12px;'
        f'background:rgba(99,102,241,0.15);'
        f'border:1px solid rgba(99,102,241,0.3);border-radius:8px;'
        f'display:flex;align-items:center;gap:10px;">'
        f'{mi("smart_toy","#818CF8","16px")}'
        f'<div><div style="font-size:12px;font-weight:600;color:#C7D2FE;">'
        f'{model_name}</div>'
        f'<div style="font-size:11px;color:#94A3B8;">Active model</div>'
        f'</div></div>'
        f'<hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);'
        f'margin:0 0 16px;">'
        f'<div style="font-size:10px;font-weight:700;letter-spacing:2px;'
        f'text-transform:uppercase;color:#64748B;margin-bottom:12px;">'
        f'Agent Pipeline</div>',
        unsafe_allow_html=True
    )

    pipeline = [
        ("security",            "#FB7185", "Security Node",    "Python · zero LLM cost"),
        ("account_tree",        "#60A5FA", "Structure Agent",  "Date · people · topics"),
        ("sentiment_satisfied", "#34D399", "Sentiment Agent",  "Tone · energy · score"),
        ("task_alt",            "#A78BFA", "Action Extractor", "Tasks · owners · priority"),
        ("summarize",           "#FBBF24", "Summary Writer",   "Report + .ics file"),
        ("how_to_reg",          "#F472B6", "Human Approval",   "HITL — you decide"),
        ("save",                "#6EE7B7", "MCP File Output",  "To outputs/ only"),
    ]
    for ic, color, title, sub in pipeline:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;'
            f'padding:8px 4px;margin:2px 0;">'
            f'<div style="width:30px;height:30px;border-radius:8px;'
            f'background:rgba(255,255,255,0.06);flex-shrink:0;'
            f'display:flex;align-items:center;justify-content:center;">'
            f'{mi(ic,color,"16px")}</div>'
            f'<div><div style="font-size:13px;font-weight:500;">{title}</div>'
            f'<div style="font-size:11px;color:#94A3B8;margin-top:1px;">'
            f'{sub}</div></div></div>',
            unsafe_allow_html=True
        )

    st.markdown(
        f'<hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);'
        f'margin:16px 0;">'
        f'<div style="font-size:10px;font-weight:700;letter-spacing:2px;'
        f'text-transform:uppercase;color:#64748B;margin-bottom:12px;">'
        f'Security</div>',
        unsafe_allow_html=True
    )
    for ic, lbl in [
        ("verified_user",   "PII scrubbing active"),
        ("gpp_good",        "Injection detection"),
        ("manage_accounts", "Human-in-the-loop"),
        ("lock",            "Sandboxed output"),
    ]:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'padding:4px 0;font-size:12px;color:#CBD5E1;">'
            f'{mi(ic,"#34D399","14px")} {lbl}</div>',
            unsafe_allow_html=True
        )

    st.markdown(
        f'<hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);'
        f'margin:16px 0 12px;">'
        f'<div style="font-size:11px;color:#64748B;line-height:1.7;">'
        f'Kaggle 5-Day AI Agents Capstone<br>Concierge Agents Track</div>',
        unsafe_allow_html=True
    )


# ── Tabs — plain text labels only (no HTML in tab names) ─────────────────────
tab1, tab2, tab3 = st.tabs([
    "Process Meeting",
    "Meeting Analytics",
    "How It Works",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Process Meeting
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        # Input card
        st.markdown(
            card_open(border_color=PRIMARY) +
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
            f'{mi("upload_file",PRIMARY,"20px")}'
            f'<span style="font-size:16px;font-weight:600;color:{TEXT};">'
            f'Input Transcript</span></div>'
            f'<div style="font-size:13px;color:{TEXT2};">'
            f'Paste text, upload a file, or use the sample</div>' +
            card_close(),
            unsafe_allow_html=True
        )

        method = st.radio(
            "Method",
            ["Paste text", "Upload file", "Use sample"],
            horizontal=True,
            label_visibility="collapsed"
        )

        transcript_text = ""
        filename = "meeting"

        if method == "Paste text":
            transcript_text = st.text_area(
                "Transcript", height=250,
                placeholder="Team Sync — June 27, 2026\n"
                            "Attendees: Sarah, Marcus...\n\n"
                            "Sarah: Let's get started...",
                label_visibility="collapsed"
            )
            filename = st.text_input(
                "filename", value="my_meeting",
                label_visibility="collapsed"
            )
            st.caption("Meeting name — used for output filenames")

        elif method == "Upload file":
            uploaded = st.file_uploader(
                "Upload", type=["txt", "md"],
                label_visibility="collapsed"
            )
            if uploaded:
                transcript_text = uploaded.read().decode("utf-8")
                filename = (uploaded.name
                            .replace(".txt","").replace(".md",""))
                st.markdown(
                    icon_row("check_circle",
                             f"Loaded: {uploaded.name}", SUCCESS),
                    unsafe_allow_html=True
                )
                with st.expander("Preview"):
                    st.text(transcript_text[:500] + "..."
                            if len(transcript_text) > 500
                            else transcript_text)

        elif method == "Use sample":
            sp = pathlib.Path("transcripts/sample_meeting.txt")
            if sp.exists():
                transcript_text = sp.read_text(encoding="utf-8")
                filename = "sample_meeting"
                with st.expander("View sample", expanded=True):
                    st.text(transcript_text)
            else:
                st.markdown(
                    icon_row("error",
                             "Sample not found at "
                             "transcripts/sample_meeting.txt",
                             ERROR),
                    unsafe_allow_html=True
                )

        if transcript_text:
            injection = check_prompt_injection(transcript_text)
            _, redacted = scrub_pii(transcript_text)
            words = len(transcript_text.split())
            st.markdown(
                card_open() +
                section_label("Security Pre-check") +
                icon_row("gpp_bad" if injection else "gpp_good",
                         "Injection DETECTED" if injection
                         else "No injection found",
                         ERROR if injection else SUCCESS) +
                icon_row("warning" if redacted else "verified_user",
                         f"{len(redacted)} PII item(s) will be redacted"
                         if redacted else "No PII detected",
                         WARNING if redacted else SUCCESS) +
                icon_row("article",
                         f"{words} words in transcript", INFO) +
                card_close(),
                unsafe_allow_html=True
            )

        st.markdown("<div style='height:4px'></div>",
                    unsafe_allow_html=True)
        blocked = (bool(transcript_text)
                   and check_prompt_injection(transcript_text))
        run_btn = st.button(
            "RUN AGENT PIPELINE",
            type="primary",
            disabled=not transcript_text or blocked,
            use_container_width=True,
            key="run_btn"
        )

    with col_r:
        st.markdown(
            card_open() +
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'margin-bottom:6px;">'
            f'{mi("auto_awesome",ACCENT,"20px")}'
            f'<span style="font-size:16px;font-weight:600;color:{TEXT};">'
            f'Results</span></div>'
            f'<div style="font-size:13px;color:{TEXT2};">'
            f'Summary appears here after the agent pipeline runs</div>' +
            card_close(),
            unsafe_allow_html=True
        )

        if run_btn and transcript_text:
            clean_text, redacted = scrub_pii(transcript_text)
            if redacted:
                st.markdown(
                    icon_row("info",
                             f"{len(redacted)} PII item(s) redacted",
                             INFO),
                    unsafe_allow_html=True
                )

            prog = st.progress(0)
            stat = st.empty()
            steps = [
                (10, "security",            "Running security checkpoint..."),
                (25, "account_tree",        "Structure agent analyzing..."),
                (45, "sentiment_satisfied", "Sentiment agent reading tone..."),
                (65, "task_alt",            "Action extractor finding tasks..."),
                (85, "summarize",           "Summary writer formatting..."),
                (95, "how_to_reg",          "Preparing approval gate..."),
            ]
            for pct, ic, msg in steps:
                prog.progress(pct)
                stat.markdown(
                    icon_row(ic, msg, PRIMARY),
                    unsafe_allow_html=True
                )
                time.sleep(0.4)

            async def run_pipeline(text):
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
                        user_id="web_user",
                    )
                    message = types.Content(
                        role="user",
                        parts=[types.Part(
                            text=f"Process this meeting transcript:\n\n{text}"
                        )]
                    )
                    # Keep only the final summary_agent output from the
                    # multi-agent pipeline (intermediate JSON from the other
                    # specialists is not part of the deliverable).
                    by_author = {}
                    async for event in runner.run_async(
                        user_id="web_user",
                        session_id=session.id,
                        new_message=message
                    ):
                        if event.content and event.content.parts:
                            for part in event.content.parts:
                                if hasattr(part, "text") and part.text:
                                    a = event.author or "agent"
                                    by_author[a] = by_author.get(a, "") + part.text
                    if "summary_agent" in by_author:
                        return by_author["summary_agent"]
                    return "".join(by_author.values())
                except Exception:
                    try:
                        from google import genai
                        key = os.getenv("GEMINI_API_KEY")
                        if not key:
                            return "ERROR: No GEMINI_API_KEY in .env"
                        client = genai.Client(api_key=key)
                        from app.agent import FULL_INSTRUCTION
                        r = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=f"{FULL_INSTRUCTION}\n\nTRANSCRIPT:\n{text}",
                        )
                        return r.text
                    except Exception as e2:
                        return f"ERROR: {e2}"

            result = asyncio.run(run_pipeline(clean_text))
            prog.progress(100)
            stat.empty()

            if result.startswith("ERROR:"):
                st.error(result)
            else:
                if "---ICS_START---" in result:
                    parts = result.split("---ICS_START---", 1)
                    summary = re.sub(
                        r"<a2ui-json>.*?</a2ui-json>", "",
                        parts[0], flags=re.DOTALL
                    ).strip()
                    calendar = parts[1].strip()
                else:
                    summary = result.strip()
                    calendar = _basic_ics()

                st.session_state.update({
                    "summary":  summary,
                    "calendar": calendar,
                    "filename": filename,
                    "redacted": redacted,
                    "ready":    True,
                    "approved": False,
                })

        if st.session_state.get("ready"):
            summary  = st.session_state["summary"]
            calendar = st.session_state["calendar"]
            fname    = st.session_state["filename"]

            lines = summary.split("\n")
            action_count = len([
                l for l in lines
                if l.startswith("|") and "Owner" not in l
                and "---" not in l and l.strip() != "|"
                and len(l.strip()) > 2
            ])
            cal_events = calendar.count("BEGIN:VEVENT")
            word_count = len(summary.split())

            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(
                    metric_card(action_count, "Action Items", "task_alt"),
                    unsafe_allow_html=True)
            with m2:
                st.markdown(
                    metric_card(cal_events, "Events", "event"),
                    unsafe_allow_html=True)
            with m3:
                st.markdown(
                    metric_card(word_count, "Words", "article"),
                    unsafe_allow_html=True)

            st.markdown("<div style='height:12px'></div>",
                        unsafe_allow_html=True)
            st.markdown(summary)

            banner_bg = "#1C1F2E" if dark else "#FFFBEB"
            banner_hd = "#FCD34D" if dark else "#92400E"
            banner_bd = "#94A3B8" if dark else "#B45309"
            st.markdown(
                f'<div style="background:{banner_bg};'
                f'border:1px solid #F59E0B;border-radius:12px;'
                f'padding:16px 20px;'
                f'display:flex;align-items:flex-start;gap:14px;margin:16px 0;">'
                f'{mi("warning_amber","#F59E0B","22px")}'
                f'<div><div style="font-size:14px;font-weight:600;'
                f'color:{banner_hd};">Human Approval Required</div>'
                f'<div style="font-size:12px;color:{banner_bd};margin-top:3px;">'
                f'Review the summary above. No files are saved until you approve. '
                f'This is the Human-in-the-Loop security gate.</div>'
                f'</div></div>',
                unsafe_allow_html=True
            )

            c1, c2 = st.columns(2)
            with c1:
                if st.button("APPROVE & SAVE", type="primary",
                             use_container_width=True, key="approve"):
                    out = pathlib.Path("outputs")
                    out.mkdir(exist_ok=True)
                    (out / f"{fname}_summary.txt").write_text(
                        summary, encoding="utf-8")
                    (out / f"{fname}.ics").write_text(
                        calendar, encoding="utf-8")
                    st.session_state["approved"] = True
            with c2:
                if st.button("REJECT & DISCARD",
                             use_container_width=True, key="reject"):
                    st.info("Discarded — no files saved.")
                    st.session_state["ready"] = False
                    st.session_state["approved"] = False

            # Render the save confirmation + downloads OUTSIDE the approve
            # button's if-block so they survive the rerun a download click
            # triggers (Streamlit reruns the whole script on every click).
            if st.session_state.get("approved"):
                st.success("Saved to outputs/ folder")
                d1, d2 = st.columns(2)
                with d1:
                    st.download_button(
                        "DOWNLOAD SUMMARY", summary,
                        file_name=f"{fname}_summary.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                with d2:
                    st.download_button(
                        "DOWNLOAD CALENDAR", calendar,
                        file_name=f"{fname}.ics",
                        mime="text/calendar",
                        use_container_width=True
                    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Meeting Analytics
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    if st.session_state.get("summary"):
        summary = st.session_state["summary"]
        tone_line = next(
            (l for l in summary.split("\n") if "Collaboration:" in l), ""
        )
        tone_map = {
            "positive": ("sentiment_very_satisfied", SUCCESS,  "Positive"),
            "tense":    ("sentiment_very_dissatisfied", ERROR, "Tense"),
            "mixed":    ("sentiment_neutral", WARNING,         "Mixed"),
            "neutral":  ("sentiment_neutral", PRIMARY,         "Neutral"),
        }
        detected = "neutral"
        for t in tone_map:
            if t in tone_line.lower():
                detected = t
                break
        t_icon, t_color, t_label = tone_map[detected]
        collab_m = re.search(r"(\d+)/10", tone_line)
        collab   = int(collab_m.group(1)) if collab_m else 5

        a1, a2 = st.columns(2)
        with a1:
            st.markdown(
                card_open(border_color=t_color) +
                section_label("Meeting Tone") +
                f'<div style="display:flex;align-items:center;gap:16px;'
                f'margin:12px 0;">'
                f'<div style="width:52px;height:52px;border-radius:50%;'
                f'background:{ICON_BG};flex-shrink:0;display:flex;'
                f'align-items:center;justify-content:center;">'
                f'{mi(t_icon,t_color,"28px")}</div>'
                f'<div><div style="font-size:24px;font-weight:300;'
                f'color:{t_color};">{t_label}</div>'
                f'<div style="font-size:12px;color:{TEXT2};margin-top:2px;">'
                f'Collaboration: {collab}/10</div></div></div>' +
                card_close(),
                unsafe_allow_html=True
            )
            st.progress(collab / 10)

        with a2:
            high = len([l for l in summary.split("\n")
                        if l.startswith("|") and "HIGH" in l])
            med  = len([l for l in summary.split("\n")
                        if l.startswith("|") and "MEDIUM" in l])
            low  = len([l for l in summary.split("\n")
                        if l.startswith("|") and "LOW" in l])
            st.markdown(
                card_open(border_color=PRIMARY) +
                section_label("Action Item Priorities") +
                icon_row("circle", f"High — {high} item(s)", ERROR) +
                icon_row("circle", f"Medium — {med} item(s)", WARNING) +
                icon_row("circle", f"Low — {low} item(s)", SUCCESS) +
                card_close(),
                unsafe_allow_html=True
            )
            if high + med + low > 0:
                try:
                    import pandas as pd
                    st.bar_chart(pd.DataFrame(
                        {"Items": [high, med, low]},
                        index=["High", "Medium", "Low"]
                    ))
                except ImportError:
                    pass

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown(
            f'''<div style="background:{SURFACE};border-radius:12px;
            box-shadow:{CARD_SH};padding:20px 24px;margin-top:8px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:2px;
            text-transform:uppercase;color:{TEXT3};margin-bottom:12px;">
            Full Summary</div>''',
            unsafe_allow_html=True
        )
        st.markdown(summary)
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.markdown(
            f'<div style="background:{SURFACE};border-radius:16px;'
            f'box-shadow:{CARD_SH};padding:64px;text-align:center;">'
            f'{mi("bar_chart",TEXT3,"52px")}'
            f'<div style="font-size:18px;font-weight:300;color:{TEXT2};'
            f'margin-top:16px;">No data yet</div>'
            f'<div style="font-size:13px;color:{TEXT3};margin-top:6px;">'
            f'Process a meeting in Tab 1 to see analytics</div></div>',
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — How It Works
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    t1, t2 = st.columns([1, 1], gap="large")

    with t1:
        # Concepts table
        concepts = [
            ("account_tree",        "Multi-agent system (ADK)",
             "4 specialist agents in a SequentialAgent pipeline"),
            ("electrical_services", "MCP Server",
             "FastMCP server for sandboxed file I/O"),
            ("security",            "Security features",
             "PII scrub · injection detect · HITL gate"),
            ("auto_stories",        "Agent Skill",
             "SKILL.md loaded on demand only"),
            ("sync_alt",            "Gemini + Claude",
             "One .env line switches AI models"),
        ]
        table_rows = "".join(
            concept_row(ic, title, desc)
            for ic, title, desc in concepts
        )
        st.markdown(
            card_open() +
            section_label("Concepts Demonstrated") +
            f'<table style="width:100%;border-collapse:collapse;">'
            f'{table_rows}</table>' +
            card_close(),
            unsafe_allow_html=True
        )

        # Security layers
        layers = [
            ("filter_1", ERROR,   "Before AI",
             "PII scrubber + injection detector run on raw text"),
            ("filter_2", WARNING, "During AI",
             "Each agent scoped to its task — no filesystem access"),
            ("filter_3", SUCCESS, "After AI",
             "Human clicks Approve before any file is written"),
        ]
        layer_rows = "".join(
            security_layer_row(ic, color, title, desc)
            for ic, color, title, desc in layers
        )
        st.markdown(
            card_open() +
            section_label("Three Security Layers") +
            layer_rows +
            card_close(),
            unsafe_allow_html=True
        )

    with t2:
        # Pipeline detail
        pipeline_detail = [
            ("security",            "#FB7185", "Security Node",
             "Pure Python, zero LLM cost. Scrubs PII, detects injection."),
            ("account_tree",        "#60A5FA", "Structure Agent",
             "Extracts date, participant names, discussion topics."),
            ("sentiment_satisfied", "#34D399", "Sentiment Agent",
             "Reads tone, energy level, collaboration score."),
            ("task_alt",            "#A78BFA", "Action Extractor",
             "Finds commitments with owner, task, deadline, priority."),
            ("summarize",           "#FBBF24", "Summary Writer",
             "Produces formatted report and .ics calendar file."),
            ("how_to_reg",          "#F472B6", "Human Approval Gate",
             "You review and approve. Nothing saved without consent."),
            ("save",                "#6EE7B7", "MCP File Output",
             "Files saved via FastMCP, restricted to outputs/ only."),
        ]
        detail_rows = "".join(
            pipeline_row(ic, color, title, desc)
            for ic, color, title, desc in pipeline_detail
        )
        st.markdown(
            card_open() +
            section_label("Agent Pipeline — Step by Step") +
            detail_rows +
            card_close(),
            unsafe_allow_html=True
        )

        # Model switching
        st.markdown(
            card_open() +
            section_label("Switching Models") +
            f'<div style="background:{CODE_BG};border-radius:8px;'
            f'padding:14px 18px;font-family:monospace;font-size:13px;'
            f'margin:10px 0;border-left:3px solid {PRIMARY};">'
            f'<span style="color:#60A5FA;">MODEL_PROVIDER</span>'
            f'<span style="color:#A78BFA;">=gemini</span><br>'
            f'<span style="color:#60A5FA;">MODEL_PROVIDER</span>'
            f'<span style="color:#A78BFA;">=claude</span></div>'
            f'<div style="font-size:12px;color:{TEXT2};">'
            f'Edit one line in your .env file. '
            f'The agent code is identical — only the model changes.</div>' +
            card_close(),
            unsafe_allow_html=True
        )