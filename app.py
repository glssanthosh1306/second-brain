"""SecondSelf — Streamlit Web Application

Clean & exact implementation matching reference UI design:
  - Header: Brain Icon title, tagline, top-right Refresh graph button, info banner box.
  - Ask Your Brain section: Red 'Ask' button inline with input, answer output, bulleted sources list with green code badges.
  - Knowledge Graph section: Embedded interactive vis-network force-directed graph.
  - Sidebar: Capture note form, Pipeline process button, Stats section (Wiki notes, Graph nodes, Graph edges).
"""

import json
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# Import SecondSelf modules
from ask import ask
from capture import capture_note, capture_link, capture_file
from pipeline import run_full_pipeline
from config import ensure_project_dirs

# Ensure directories exist on startup
ensure_project_dirs()

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
GRAPH_JSON_PATH = DATA_DIR / "graph.json"
GRAPH_HTML_PATH = ROOT / "static" / "graph.html"
WIKI_DIR = ROOT / "wiki"
RAW_DIR = ROOT / "raw"

# Page Configuration
st.set_page_config(
    page_title="SecondSelf — Your personal AI second brain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject custom CSS to match reference image UI and suppress broken images
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Hide any broken img tags at top left */
    [data-testid="stSidebarHeader"] img,
    img[alt="0"],
    .stApp header img,
    .stSidebar img {
        display: none !important;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Header styling */
    .app-title-container {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 4px;
    }
    .app-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
    }
    .app-subtitle {
        font-size: 0.95rem;
        color: #94a3b8;
        margin-bottom: 1rem;
    }

    /* Info Banner Box */
    .info-banner {
        background-color: rgba(30, 58, 138, 0.35);
        border: 1px solid rgba(59, 130, 246, 0.4);
        color: #93c5fd;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        font-size: 0.88rem;
        margin-bottom: 1.75rem;
    }

    /* Section Headings */
    .section-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }

    /* Primary Red Buttons */
    div.stButton > button[kind="primary"],
    div.stFormSubmitButton > button {
        background-color: #ff4b4b !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        height: 42px;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stFormSubmitButton > button:hover {
        background-color: #ff3333 !important;
    }

    /* Source Green Code Badges */
    .source-badge-code {
        background-color: rgba(74, 222, 128, 0.15);
        color: #4ade80;
        font-family: monospace;
        font-size: 0.85rem;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 600;
    }

    .source-item {
        margin-bottom: 6px;
        font-size: 0.92rem;
        line-height: 1.6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=60)
def load_graph_stats():
    """Load graph node and edge counts."""
    if not GRAPH_JSON_PATH.is_file():
        return {"nodes": 0, "edges": 0, "para_counts": {}}
    try:
        with open(GRAPH_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        para_counts = {}
        for n in nodes:
            grp = n.get("group", "Unclassified")
            para_counts[grp] = para_counts.get(grp, 0) + 1
        return {
            "nodes": len(nodes),
            "edges": len(edges),
            "para_counts": para_counts,
        }
    except Exception:
        return {"nodes": 0, "edges": 0, "para_counts": {}}


# ===========================================================================
# SIDEBAR
# ===========================================================================
with st.sidebar:
    st.markdown("## **Capture**")
    st.caption("Quick note")

    with st.form("sidebar_capture_form", clear_on_submit=True):
        note_input = st.text_area(
            "Quick note",
            placeholder="Capture a thought, task, or insight...",
            label_visibility="collapsed",
            height=100,
        )
        submitted_capture = st.form_submit_button("Capture note", use_container_width=True)
        if submitted_capture and note_input.strip():
            cid = capture_note(note_input)
            st.success(f"Captured note: `{cid}`")

    st.markdown("---")

    st.markdown("## **Pipeline**")
    force_reprocess = st.checkbox("Force re-process")
    if st.button("Process new captures", use_container_width=True, type="primary"):
        with st.spinner("Processing captures & rebuilding pipeline..."):
            res = run_full_pipeline()
            if res == 0:
                st.cache_data.clear()
                st.success("Pipeline processing complete!")
                st.rerun()
            else:
                st.error("Pipeline run encountered an error.")

    st.markdown("---")

    st.markdown("## **Stats**")
    stats = load_graph_stats()
    st.markdown(f"**Wiki notes**\n### {stats['nodes']}")
    st.markdown(f"**Graph nodes**\n### {stats['nodes']}")
    st.markdown(f"**Graph edges**\n### {stats['edges']}")


# ===========================================================================
# MAIN PAGE CONTENT
# ===========================================================================

# Header & Top Action
col_title, col_btn = st.columns([4, 1])

with col_title:
    st.markdown(
        '<div class="app-title-container"><span style="font-size: 2.2rem;">🧠</span><span class="app-title">SecondSelf</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="app-subtitle">Your personal AI second brain — capture, organize, explore, ask.</div>',
        unsafe_allow_html=True,
    )

with col_btn:
    st.write("")  # vertical spacing
    if st.button("Refresh graph", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Info Banner
st.markdown(
    '<div class="info-banner">Hosted demo: the graph and bundled notes load from the repo. Captures and pipeline changes are session-only and reset on redeploy.</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# SECTION 1: ASK YOUR BRAIN
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Ask your brain</div>', unsafe_allow_html=True)

with st.form("ask_form", clear_on_submit=False):
    col_input, col_ask = st.columns([5, 1])
    with col_input:
        user_query = st.text_input(
            "Question",
            placeholder="Do you know about masai live class ?",
            label_visibility="collapsed",
        )
    with col_ask:
        ask_submitted = st.form_submit_button("Ask", use_container_width=True)

if ask_submitted and user_query.strip():
    with st.spinner("Synthesizing answer..."):
        try:
            ans = ask(user_query.strip())

            # Answer Output
            st.markdown(
                f"<div style='font-size:1.05rem; line-height:1.6; margin-top:0.75rem; margin-bottom:1.5rem;'>{ans.text}</div>",
                unsafe_allow_html=True,
            )

            # Sources Section
            if hasattr(ans, "retrieved_sources") and ans.retrieved_sources:
                st.markdown("#### **Sources**")
                for src in ans.retrieved_sources:
                    short_id = src.id[-8:] if len(src.id) > 8 else src.id
                    category = src.category or "Resources"
                    score_str = f"{src.score:.3f}"
                    summary = src.title or (src.content[:90].replace('\n', ' ') + "...")

                    source_html = f"""
                    <div class="source-item">
                        • <span class="source-badge-code">{short_id}</span> · <strong>{category}</strong> · score <strong>{score_str}</strong> — {summary}
                    </div>
                    """
                    st.markdown(source_html, unsafe_allow_html=True)

            elif ans.sources:
                st.markdown("#### **Sources**")
                for sid in ans.sources:
                    short_id = sid[-8:] if len(sid) > 8 else sid
                    source_html = f"""
                    <div class="source-item">
                        • <span class="source-badge-code">{short_id}</span> · <strong>Resources</strong> — Cited note {sid}
                    </div>
                    """
                    st.markdown(source_html, unsafe_allow_html=True)

        except Exception as err:
            st.error(f"⚠️ Error asking brain: {err}")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SECTION 2: KNOWLEDGE GRAPH
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Knowledge graph</div>', unsafe_allow_html=True)

if GRAPH_HTML_PATH.is_file():
    with open(GRAPH_HTML_PATH, "r", encoding="utf-8") as f:
        html_content = f.read()
    components.html(html_content, height=650, scrolling=False)
else:
    st.warning("Knowledge graph HTML not built yet. Click 'Process new captures' in the sidebar to generate it.")
