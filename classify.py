"""SecondSelf — Auto-Classification Pipeline (Phase 2.2: The Librarian)

Scans raw/ captures, uses Groq (llama-3.1-8b-instant) to categorize notes
into PARA (Projects, Areas, Resources, Archives), extract tags and a summary,
and creates structured wiki notes with YAML frontmatter.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
import frontmatter

from config import (
    DATA_DIR,
    NOTE_REGISTRY,
    PARA_FOLDERS,
    RAW_DIR,
    WIKI_DIR,
    ensure_project_dirs,
)

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

try:
    from groq import Groq
except ImportError:
    Groq = None


def get_groq_client() -> Optional[Any]:
    """Instantiate Groq client if key and library are available."""
    api_key = get_groq_api_key()
    if not api_key or Groq is None:
        return None
    try:
        return Groq(api_key=api_key)
    except Exception as e:
        print(f"Warning: Failed to initialize Groq client: {e}", file=sys.stderr)
        return None


def load_note_registry() -> Dict[str, Any]:
    """Load or initialize note_registry.json."""
    ensure_project_dirs()
    if NOTE_REGISTRY.exists():
        try:
            with open(NOTE_REGISTRY, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_note_registry(registry: Dict[str, Any]) -> None:
    """Save updated note_registry.json."""
    ensure_project_dirs()
    with open(NOTE_REGISTRY, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


import argparse
import datetime

def parse_llm_response(text: str) -> Dict[str, Any]:
    """Parse JSON response from Groq LLM."""
    try:
        # Sometimes the LLM wraps JSON in markdown blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        parsed = json.loads(text.strip())
        return {
            "para": parsed.get("para", "Archives").strip(),
            "tags": [t.strip() for t in parsed.get("tags", []) if isinstance(t, str)],
            "summary": parsed.get("summary", "").strip(),
            "title": parsed.get("title", "").strip()
        }
    except Exception as e:
        print(f"Warning: Failed to parse LLM JSON: {e}", file=sys.stderr)
        return {"para": "Archives", "tags": ["unclassified"], "summary": "Failed to classify.", "title": ""}

def classify_capture(capture_id: str) -> Path:
    """Classify a capture using Groq and save to wiki."""
    capture_dir = RAW_DIR / capture_id
    content_file = capture_dir / "content.md"
    meta_file = capture_dir / "meta.json"

    if not content_file.exists() or not meta_file.exists():
        raise FileNotFoundError(f"Missing content.md or meta.json for {capture_id}")

    with open(content_file, "r", encoding="utf-8") as f:
        content = f.read()

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    client = get_groq_client()
    
    if client:
        system_prompt = (
            "You classify notes using PARA (Projects, Areas, Resources, Archives).\n"
            "Valid categories are exactly one of: 'Projects', 'Areas', 'Resources', 'Archives'.\n"
            "Return ONLY valid JSON matching this schema:\n"
            "{ \"para\": \"...\", \"tags\": [\"...\", \"...\"], \"summary\": \"...\", \"title\": \"...\" }\n"
            "Do not include any other text."
        )
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Classify this capture:\n\n{content}"}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.3,
            )
            llm_text = chat_completion.choices[0].message.content
            classification = parse_llm_response(llm_text)
        except Exception as e:
            print(f"Warning: Groq API call failed: {e}", file=sys.stderr)
            classification = {"para": "Archives", "tags": ["error"], "summary": "API error.", "title": capture_id}
    else:
        classification = {"para": "Archives", "tags": ["unclassified"], "summary": "No API key.", "title": capture_id}

    # Validate PARA category
    category = classification["para"]
    if category not in PARA_FOLDERS:
        category = "Archives"

    # Determine filename
    title = classification.get("title") or capture_id
    safe_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', title).strip().replace(' ', '_')
    if not safe_title:
        safe_title = capture_id
    
    filename = f"{capture_id}_{safe_title}.md"
    
    # Create frontmatter
    post = frontmatter.Post(content)
    post['id'] = capture_id
    post['title'] = title
    post['date'] = meta.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat())
    post['category'] = category
    post['tags'] = classification["tags"]
    post['summary'] = classification["summary"]
    post['source'] = meta.get("source", "unknown")

    # Save to wiki
    out_dir = WIKI_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))

    # Update meta.json
    meta["processed"] = True
    meta["wiki_path"] = str(out_path.relative_to(WIKI_DIR))
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # Update registry
    registry = load_note_registry()
    registry[capture_id] = {
        "wiki_path": str(out_path.relative_to(WIKI_DIR)),
        "category": category,
        "tags": classification["tags"],
        "title": title
    }
    save_note_registry(registry)

    return out_path

def list_unprocessed_captures(force: bool = False) -> List[str]:
    """List capture IDs in raw/ that have not yet been converted into wiki notes."""
    ensure_project_dirs()
    if not RAW_DIR.exists():
        return []

    registry = load_note_registry()
    unprocessed = []

    for cdir in sorted(RAW_DIR.iterdir()):
        if not cdir.is_dir() or cdir.name.startswith("."):
            continue
        capture_id = cdir.name
        meta_file = cdir / "meta.json"
        if not meta_file.exists():
            continue

        if not force:
            # Check if marked processed in meta.json or registry
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if meta.get("processed") is True or capture_id in registry:
                    continue
            except Exception:
                pass

        unprocessed.append(capture_id)

    return unprocessed

def classify_all_unprocessed(force: bool = False) -> List[Path]:
    """Batch classify all unprocessed raw captures."""
    unprocessed = list_unprocessed_captures(force=force)
    if not unprocessed:
        print("No unprocessed captures found in raw/.")
        return []

    print(f"Found {len(unprocessed)} unprocessed capture(s). Starting classification...")
    processed_paths = []

    for cid in unprocessed:
        try:
            path = classify_capture(cid)
            processed_paths.append(path)
            rel_path = path.relative_to(WIKI_DIR)
            print(f"[OK] Classified [{cid}] -> wiki/{rel_path}")
        except Exception as err:
            print(f"Error classifying {cid}: {err}", file=sys.stderr)

    return processed_paths

def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-Classify raw captures into wiki notes.")
    parser.add_argument("--force", action="store_true", help="Force re-classification of all captures.")
    args = parser.parse_args()

    ensure_project_dirs()
    paths = classify_all_unprocessed(force=args.force)
    print(f"\nSuccessfully classified {len(paths)} note(s) into wiki/.")

if __name__ == "__main__":
    main()
