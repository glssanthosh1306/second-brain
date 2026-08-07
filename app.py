"""SecondSelf — Streamlit Web Application (Phase 4)

Interactive UI combining:
  1. Header & Quick Search / RAG Ask Interface (ask.py)
  2. Answer Display with Cited Sources & Note Previews
  3. Interactive Force-Directed Brain Graph (vis-network embedding)
  4. Sidebar: Brain Stats, Capture Form (capture.py), & Pipeline Refresh (pipeline.py)
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
    page_title="SecondSelf — Your Personal AI Second Brain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Premium Design
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Gradient Header Title */
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #a855f7 0%, #ec4899 50%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }

    .sub-title {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }

    /* Glassmorphic Card Container */
    .glass-card {
        background: rgba(30, 41, 59, 0.5);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.25rem;
        margin-bottom: 1.5rem;
    }

    /* Source Badge */
    .source-badge {
        display: inline-block;
        background: rgba(168, 85, 247, 0.2);
        color: #c084fc;
        border: 1px solid rgba(168, 85, 247, 0.4);
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 6px;
        margin-top: 6px;
    }

    /* Streamlit Button Tweaks */
    div.stButton > button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
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
    st.image("https://img.icons8.com/gradient/96/brain.png", width=64)
    st.title("SecondSelf Control Center")

    st.markdown("---")
    st.subheader("📊 Brain Stats")
    stats = load_graph_stats()
    col1, col2 = st.columns(2)
    col1.metric("Total Notes", stats["nodes"])
    col2.metric("Auto Links", stats["edges"])

    if stats["para_counts"]:
        st.markdown("**PARA Breakdown:**")
        for para, cnt in stats["para_counts"].items():
            st.caption(f"• **{para}**: {cnt} notes")

    st.markdown("---")

    # Quick Capture Section
    st.subheader("⚡ Quick Capture")
    capture_type = st.radio("Capture Type", ["Text Note", "Web Link", "File"], horizontal=True)

    with st.form("quick_capture_form", clear_on_submit=True):
        if capture_type == "Text Note":
            note_text = st.text_area("Note Content", placeholder="Capture an idea, thought, or snippet...")
            submitted = st.form_submit_button("📥 Capture Note", use_container_width=True)
            if submitted and note_text.strip():
                cid = capture_note(note_text)
                st.success(f"Captured note! ID: `{cid}`")
                st.info("Click 'Refresh Brain' below to classify & link your new capture.")

        elif capture_type == "Web Link":
            link_url = st.text_input("URL", placeholder="https://example.com/article")
            submitted = st.form_submit_button("🔗 Capture Link", use_container_width=True)
            if submitted and link_url.strip():
                cid = capture_link(link_url)
                st.success(f"Captured link! ID: `{cid}`")
                st.info("Click 'Refresh Brain' below to process.")

        elif capture_type == "File":
            uploaded = st.file_uploader("Upload File (PDF / TXT / MD)")
            submitted = st.form_submit_button("📁 Capture File", use_container_width=True)
            if submitted and uploaded:
                tmp_dir = ROOT / "scratch"
                tmp_dir.mkdir(exist_ok=True)
                tmp_path = tmp_dir / uploaded.name
                with open(tmp_path, "wb") as f:
                    f.write(uploaded.getbuffer())
                cid = capture_file(str(tmp_path))
                st.success(f"Captured file! ID: `{cid}`")
                st.info("Click 'Refresh Brain' below to process.")

    st.markdown("---")

    # Pipeline Trigger Button
    st.subheader("🔄 Pipeline Runner")
    if st.button("🚀 Refresh Brain Pipeline", use_container_width=True, help="Runs classify → link → build_graph"):
        with st.spinner("Processing captures, computing embeddings & rebuilding graph..."):
            res = run_full_pipeline()
            if res == 0:
                st.cache_data.clear()
                st.success("Pipeline refreshed successfully!")
                st.rerun()
            else:
                st.error("Pipeline run encountered an error.")


# ===========================================================================
# MAIN PAGE CONTENT
# ===========================================================================

# Header Banner
st.markdown('<div class="main-title">SecondSelf</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Your Personal AI Second Brain — Self-Organizing Knowledge Base & RAG Oracle</div>',
    unsafe_allow_html=True,
)

# Tabs Navigation
tab_ask, tab_graph = st.tabs(["💬 Ask Your Brain", "🕸️ Interactive Brain Graph"])

# ---------------------------------------------------------------------------
# TAB 1: ASK YOUR BRAIN (RAG QA)
# ---------------------------------------------------------------------------
with tab_ask:
    st.markdown("##### Ask any question across your personal notes, links, and documents:")

    with st.form("ask_form"):
        user_query = st.text_input(
            "Question",
            placeholder="e.g. What notes have I saved about RAG architectures or machine learning?",
            label_visibility="collapsed",
        )
        ask_button = st.form_submit_button("✨ Ask Brain", use_container_width=True)

    if ask_button and user_query.strip():
        with st.spinner("Searching personal knowledge base & synthesizing answer via Groq..."):
            try:
                ans = ask(user_query.strip())
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.subheader("Answer")
                st.markdown(ans.text)

                if ans.sources:
                    st.markdown("---")
                    st.markdown("**Source Notes Cited:**")
                    sources_html = "".join([f'<span class="source-badge">📄 {src}</span>' for src in ans.sources])
                    st.markdown(sources_html, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            except Exception as err:
                st.error(f"⚠️ Error asking brain: {err}")

    elif not ask_button:
        st.info("💡 **Tip**: Type a question above to retrieve context from your PARA wiki notes and synthesize grounded answers with citations.")


# ---------------------------------------------------------------------------
# TAB 2: INTERACTIVE BRAIN GRAPH
# ---------------------------------------------------------------------------
with tab_graph:
    st.markdown("##### Force-Directed Knowledge Graph (Projects, Areas, Resources, Archives)")

    if GRAPH_HTML_PATH.is_file():
        with open(GRAPH_HTML_PATH, "r", encoding="utf-8") as f:
            html_content = f.read()
        components.html(html_content, height=650, scrolling=False)
    else:
        st.warning("Graph HTML not built yet. Click 'Refresh Brain Pipeline' in the sidebar to generate it.")
