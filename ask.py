# ask.py – Retrieval‑Augmented Generation module for Phase 4
"""Implementation of the RAG component (`ask.py`).

Provides a high‑level `ask(question: str) -> Answer` function used by the
Streamlit UI. The module:
  1. Loads the note registry and pre‑computed embeddings (cached in memory).
  2. Retrieves the most similar notes for a query using cosine similarity.
  3. Builds a context block for the LLM.
  4. Calls Groq's `llama-3.1-8b-instant` model with a grounding prompt.
  5. Returns an `Answer` dataclass containing the answer text, cited note IDs
     and an optional confidence score.

Dependencies:
  - sentence_transformers (for on‑the‑fly query embedding)
  - numpy, scikit‑learn (cosine similarity)
  - groq (Groq API client)
  - python-dotenv (load `GROQ_API_KEY` from `.env`)
  - pathlib, json, pickle, dataclasses, typing
"""

import json
import logging
import os
import pickle
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

# Suppress Hugging Face, Transformers, and tqdm output warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN_WARNING"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TQDM_DISABLE"] = "1"
warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from groq import Groq
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment & configuration
# ---------------------------------------------------------------------------
def get_groq_api_key() -> str:
    """Retrieve GROQ_API_KEY from Streamlit secrets, environment, or .env."""
    try:
        import streamlit as st
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass

    load_dotenv()
    key = os.getenv("GROQ_API_KEY")
    if key and key != "your_key_here":
        return key

    return ""

ROOT = Path(__file__).parent
WIKI_DIR = ROOT / "wiki"
INDEX_DIR = WIKI_DIR / ".index"
EMBEDDINGS_PATH = INDEX_DIR / "embeddings.pkl"
NOTE_REGISTRY_PATH = INDEX_DIR / "note_registry.json"

# Retrieval configuration
SIMILARITY_THRESHOLD = 0.20
DEFAULT_TOP_K = 5
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# Global caches – loaded once per process for speed
# ---------------------------------------------------------------------------
_embedding_model: SentenceTransformer | None = None
# Tuple of (list[note_id], ndarray[N, 384]) — matches the pickle format
_embeddings_cache: tuple | None = None
_notes_cache: Dict[str, "WikiNote"] | None = None


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def _load_embeddings() -> tuple:
    """Load (or return cached) note embeddings.

    The pickle stores a dict with two keys:
      - ``"ids"``: list of note ID strings, length N
      - ``"vectors"``: ``np.ndarray`` of shape (N, embedding_dim)

    Returns a ``(ids, matrix)`` tuple for direct use in similarity search.
    """
    global _embeddings_cache
    if _embeddings_cache is None:
        with open(EMBEDDINGS_PATH, "rb") as f:
            data = pickle.load(f)
        # Unpack the stored structure
        ids: list = data["ids"]
        matrix: np.ndarray = data["vectors"]
        _embeddings_cache = (ids, matrix)
    return _embeddings_cache


def _load_notes() -> Dict[str, "WikiNote"]:
    """Load (or return cached) wiki notes ready for retrieval.

    The note registry JSON maps each note ID to a dict with at least:
      { "wiki_path": "<PARA>/filename.md", "category": "...", "tags": [...], "title": "..." }

    This function reads each markdown file relative to ``WIKI_DIR``, strips
    any YAML front‑matter, and caches the result for the process lifetime.
    """
    global _notes_cache
    if _notes_cache is None:
        with open(NOTE_REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry: Dict[str, dict] = json.load(f)
        notes: Dict[str, WikiNote] = {}
        for nid, entry in registry.items():
            rel_path: str = entry.get("wiki_path", "")
            title: str = entry.get("title", "")
            tags: List[str] = entry.get("tags", [])
            note_path = WIKI_DIR / rel_path
            if not note_path.is_file():
                continue
            with open(note_path, "r", encoding="utf-8") as f:
                raw = f.read()
            # Remove YAML front‑matter if present
            if raw.startswith("---"):
                parts = raw.split("---", 2)
                body = parts[2] if len(parts) == 3 else ""
            else:
                body = raw
            notes[nid] = WikiNote(
                id=nid,
                path=note_path,
                content=body.strip(),
                title=title,
                tags=tags,
            )
        _notes_cache = notes
    return _notes_cache

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class WikiNote:
    id: str
    path: Path
    content: str
    title: str = ""
    tags: List[str] = None

@dataclass
class RetrievedNote:
    id: str
    content: str
    score: float
    title: str = ""
    tags: List[str] = None

@dataclass
class Answer:
    text: str
    sources: List[str]
    confidence: float | None = None

# ---------------------------------------------------------------------------
# Retrieval pipeline
# ---------------------------------------------------------------------------
def retrieve(question: str, top_k: int = DEFAULT_TOP_K) -> List[RetrievedNote]:
    """Return the most similar notes for *question*.

    Steps:
      1. Embed the question with the same model used for note embeddings.
      2. Compute cosine similarity against the cached embedding matrix.
      3. Filter by ``SIMILARITY_THRESHOLD`` and keep the top‑K results.
    """
    ids, matrix = _load_embeddings()
    notes = _load_notes()

    model = _get_embedding_model()
    q_vec = model.encode([question])[0]

    sims = cosine_similarity([q_vec], matrix)[0]

    # Deduplicate note IDs, keeping highest score for each note ID
    scored_dict: Dict[str, float] = {}
    for nid, sim in zip(ids, sims):
        val = float(sim)
        if val >= SIMILARITY_THRESHOLD:
            if nid not in scored_dict or val > scored_dict[nid]:
                scored_dict[nid] = val

    scored = sorted(scored_dict.items(), key=lambda x: x[1], reverse=True)
    top = scored[:top_k]

    results: List[RetrievedNote] = []
    for nid, score in top:
        note = notes.get(nid)
        if note:
            results.append(
                RetrievedNote(
                    id=nid,
                    content=note.content,
                    score=score,
                    title=note.title,
                    tags=note.tags or [],
                )
            )
    return results

# ---------------------------------------------------------------------------
# Context building
# ---------------------------------------------------------------------------
def build_context(retrieved: List[RetrievedNote]) -> str:
    """Create the formatted ``Notes:`` block for the RAG prompt."""
    blocks = []
    for note in retrieved:
        body = note.content[:1000]
        title_line = f"Title: {note.title}\n" if note.title else ""
        tags_line = f"Tags: {', '.join(note.tags)}\n" if note.tags else ""
        blocks.append(f"Note ID: {note.id}\n{title_line}{tags_line}Content:\n{body}\n---")
    return "\n".join(blocks)

# ---------------------------------------------------------------------------
# LLM interaction
# ---------------------------------------------------------------------------
RAG_PROMPT_TEMPLATE = """You answer questions using the provided notes from the user's personal knowledge base.
Synthesize a clear, helpful response based on the note titles, tags, and content.
Include relevant topics found in the notes (such as AI, Machine Learning, embeddings, personal info, tools, etc.).
If the provided notes contain no relevant information at all, state that clearly.
Always cite the relevant Note IDs when referencing information from a note.

Notes:
---
{notes}
---

Question: {question}
"""

def _call_groq(prompt: str) -> str:
    api_key = get_groq_api_key()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your .env file or Streamlit secrets.")
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()

def synthesize_answer(question: str, context: str) -> Answer:
    """Run the LLM and extract cited note IDs.

    Returns an ``Answer`` instance. If the model produces no
    content we still return an empty ``Answer`` with an empty source list.
    """
    prompt = RAG_PROMPT_TEMPLATE.format(notes=context, question=question)
    raw_text = _call_groq(prompt)
    import re
    cited = re.findall(r"\b[0-9]{8}_[0-9]{6}_[a-z0-9]{6}\b", raw_text)
    seen = set()
    sources = [x for x in cited if not (x in seen or seen.add(x))]
    return Answer(text=raw_text, sources=sources)

# ---------------------------------------------------------------------------
# Public API used by Streamlit
# ---------------------------------------------------------------------------
def ask(question: str) -> Answer:
    """Answer *question* using RAG.

    1. Retrieve relevant notes.
    2. Build the prompt context.
    3. Call the LLM.
    4. Return the structured ``Answer``.
    """
    retrieved = retrieve(question)
    if not retrieved:
        return synthesize_answer(question, "")
    context = build_context(retrieved)
    return synthesize_answer(question, context)

# ---------------------------------------------------------------------------
# Simple CLI for debugging / manual testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ask a question against your wiki notes.")
    parser.add_argument("question", type=str, help="The question to answer")
    args = parser.parse_args()
    ans = ask(args.question)
    print("Answer:\n", ans.text)
    print("Sources:", ", ".join(ans.sources) if ans.sources else "<none>")
