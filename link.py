"""SecondSelf — Auto-Link Pipeline (Phase 2.3: The Librarian)

Generates vector embeddings for all markdown notes and uses cosine similarity
to automatically generate and update bidirectional links in the frontmatter.
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import frontmatter
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from config import (
    EMBEDDING_MODEL,
    EMBEDDINGS_PATH,
    PARA_FOLDERS,
    SIMILARITY_THRESHOLD,
    TOP_K_LINKS,
    WIKI_DIR,
    ensure_project_dirs,
)

# Global variables to lazy-load the model
_model = None


def load_embedding_model() -> Any:
    """Lazy-load the sentence-transformers model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model '{EMBEDDING_MODEL}'... (this may take a moment)")
            _model = SentenceTransformer(EMBEDDING_MODEL)
        except ImportError:
            print("Error: sentence-transformers is not installed.", file=sys.stderr)
            sys.exit(1)
    return _model


def embed_text(text: str) -> np.ndarray:
    """Return a numpy vector for the given text."""
    model = load_embedding_model()
    # Ensure it's a 1D array
    return model.encode(text)


def load_embedding_index() -> Dict[str, Any]:
    """Load or initialize wiki/.index/embeddings.pkl"""
    ensure_project_dirs()
    if EMBEDDINGS_PATH.exists():
        try:
            with open(EMBEDDINGS_PATH, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Warning: Failed to load embeddings index: {e}", file=sys.stderr)
            return {"ids": [], "vectors": []}
    return {"ids": [], "vectors": []}


def save_embedding_index(index: Dict[str, Any]) -> None:
    """Persist vectors + note ID mapping."""
    ensure_project_dirs()
    with open(EMBEDDINGS_PATH, "wb") as f:
        pickle.dump(index, f)


def get_all_notes() -> List[Path]:
    """Return a list of all markdown notes in the wiki PARA folders."""
    notes = []
    for folder in PARA_FOLDERS:
        folder_path = WIKI_DIR / folder
        if folder_path.exists():
            notes.extend(list(folder_path.glob("*.md")))
    return notes


def update_note_links(note_path: Path, linked_ids: List[str]) -> None:
    """Write `links:` to frontmatter."""
    try:
        with open(note_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
            
        post["links"] = linked_ids
        
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))
    except Exception as e:
        print(f"Error updating links for {note_path}: {e}", file=sys.stderr)


def process_all_notes() -> None:
    """Rebuild index and links for entire wiki."""
    notes = get_all_notes()
    if not notes:
        print("No notes found in the wiki.")
        return

    index = load_embedding_index()
    existing_ids = set(index["ids"])
    
    # Check if we have vectors, otherwise initialize correctly
    if isinstance(index["vectors"], list):
        if len(index["vectors"]) > 0:
            index["vectors"] = np.vstack(index["vectors"])
        else:
            index["vectors"] = np.empty((0, 384)) # Default size for all-MiniLM-L6-v2, will be replaced if we have actual data
            
    # Process new or updated notes
    print(f"Found {len(notes)} notes. Building/updating embeddings...")
    new_ids = []
    new_vectors = []
    
    note_id_to_path = {}
    
    for note_path in notes:
        try:
            with open(note_path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
            
            note_id = post.get("id")
            if not note_id:
                # Fallback to filename if no ID in frontmatter
                note_id = note_path.stem
                
            note_id_to_path[note_id] = note_path
                
            if note_id not in existing_ids:
                # Combine title, summary, tags, and content for a rich embedding
                text_to_embed = f"{post.get('title', '')}\n{post.get('summary', '')}\n{', '.join(post.get('tags', []))}\n{post.content}"
                vector = embed_text(text_to_embed)
                
                new_ids.append(note_id)
                new_vectors.append(vector)
                print(f"Embedded new note: {note_id}")
        except Exception as e:
            print(f"Error processing {note_path}: {e}", file=sys.stderr)

    if new_ids:
        index["ids"].extend(new_ids)
        if len(index["vectors"]) == 0:
            index["vectors"] = np.vstack(new_vectors)
        else:
            index["vectors"] = np.vstack([index["vectors"], np.vstack(new_vectors)])
        save_embedding_index(index)
        print(f"Added {len(new_ids)} new embeddings to the index.")
    else:
        print("Embeddings index is up to date.")

    # Only run linking if we have more than one note
    if len(index["ids"]) > 1:
        print(f"Calculating similarities and generating links...")
        
        vectors = index["vectors"]
        ids = index["ids"]
        
        # Calculate full pairwise cosine similarity matrix
        sim_matrix = cosine_similarity(vectors)
        
        # Ensure symmetric updates by processing row by row
        for i, note_id in enumerate(ids):
            # Get similarities for this note
            similarities = sim_matrix[i]
            
            # Find indices of notes above threshold, excluding self (i != j)
            # and sort them by similarity (descending)
            related = []
            for j, sim in enumerate(similarities):
                if i != j and sim >= SIMILARITY_THRESHOLD:
                    related.append((j, sim))
                    
            related.sort(key=lambda x: x[1], reverse=True)
            
            # Take top K
            top_related = related[:TOP_K_LINKS]
            linked_ids = [ids[idx] for idx, _ in top_related]
            
            if note_id in note_id_to_path:
                update_note_links(note_id_to_path[note_id], linked_ids)
                
        print(f"Successfully auto-linked {len(ids)} notes.")

def main() -> None:
    ensure_project_dirs()
    process_all_notes()

if __name__ == "__main__":
    main()
