"""SecondSelf — CLI Search Utility

Quick keyword search, tag filtering, category listing, and semantic search over wiki notes.
"""

from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import frontmatter

from config import (
    EMBEDDING_MODEL,
    EMBEDDINGS_PATH,
    PARA_FOLDERS,
    WIKI_DIR,
    ensure_project_dirs,
)


def load_all_wiki_notes() -> List[Dict[str, Any]]:
    """Scan wiki/ and parse all markdown notes with frontmatter."""
    ensure_project_dirs()
    notes = []
    
    for category in PARA_FOLDERS:
        folder_path = WIKI_DIR / category
        if not folder_path.exists():
            continue
            
        for filepath in folder_path.glob("*.md"):
            try:
                post = frontmatter.load(filepath)
                note_id = post.get("id", filepath.stem)
                title = post.get("title", filepath.stem)
                tags = post.get("tags", [])
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",")]
                summary = post.get("summary", "")
                cat = post.get("category", category)
                links = post.get("links", [])
                
                notes.append({
                    "id": note_id,
                    "title": title,
                    "category": cat,
                    "tags": tags,
                    "summary": summary,
                    "links": links,
                    "content": post.content,
                    "path": filepath,
                    "relative_path": filepath.relative_to(WIKI_DIR)
                })
            except Exception as e:
                print(f"Warning: Failed to load {filepath}: {e}", file=sys.stderr)
                
    return notes


def list_notes(notes: List[Dict[str, Any]], tag_filter: Optional[str] = None, category_filter: Optional[str] = None) -> None:
    """Print formatted summary list of notes."""
    filtered = notes
    
    if category_filter:
        cat_lower = category_filter.lower()
        filtered = [n for n in filtered if n["category"].lower() == cat_lower]
        
    if tag_filter:
        t_lower = tag_filter.lower()
        filtered = [n for n in filtered if any(t_lower in tag.lower() for tag in n["tags"])]

    if not filtered:
        print("No matching notes found.")
        return

    print(f"\nFound {len(filtered)} note(s):\n")
    print(f"{'CATEGORY':<12} | {'TITLE':<40} | {'TAGS':<25} | {'ID'}")
    print("-" * 105)
    for n in filtered:
        cat = n['category']
        title = (n['title'][:37] + "...") if len(n['title']) > 40 else n['title']
        tags_str = ", ".join(n['tags'])
        tags_disp = (tags_str[:22] + "...") if len(tags_str) > 25 else tags_str
        print(f"{cat:<12} | {title:<40} | {tags_disp:<25} | {n['id']}")
    print()


def keyword_search(notes: List[Dict[str, Any]], query: str) -> None:
    """Case-insensitive keyword search across title, tags, summary, and content body."""
    q = query.lower()
    matches = []
    
    for n in notes:
        title_match = q in n["title"].lower()
        summary_match = q in n["summary"].lower()
        tag_match = any(q in t.lower() for t in n["tags"])
        content_match = q in n["content"].lower()
        cat_match = q in n["category"].lower()
        id_match = q in n["id"].lower()

        if title_match or summary_match or tag_match or content_match or cat_match or id_match:
            # Highlight snippet if found in content
            snippet = ""
            if content_match:
                lines = n["content"].splitlines()
                matching_lines = [line.strip() for line in lines if q in line.lower()]
                if matching_lines:
                    snippet = matching_lines[0]
                    if len(snippet) > 100:
                        snippet = snippet[:97] + "..."
            elif summary_match:
                snippet = n["summary"]
                
            matches.append((n, snippet))

    if not matches:
        print(f"No notes matching '{query}'.")
        return

    print(f"\nFound {len(matches)} match(es) for query '{query}':\n")
    for n, snippet in matches:
        print(f"[{n['category']}] {n['title']} ({n['path'].name})")
        print(f"  ID:      {n['id']}")
        print(f"  Tags:    {', '.join(n['tags'])}")
        if snippet:
            print(f"  Match:   {snippet}")
        print()


def semantic_search(notes: List[Dict[str, Any]], query: str, top_k: int = 5) -> None:
    """Semantic vector similarity search using stored embeddings."""
    if not EMBEDDINGS_PATH.exists():
        print(f"Embeddings index not found at {EMBEDDINGS_PATH}. Please run `python link.py` first.", file=sys.stderr)
        return

    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
    except ImportError:
        print("Missing ML dependencies. Please install sentence-transformers and scikit-learn.", file=sys.stderr)
        return

    with open(EMBEDDINGS_PATH, "rb") as f:
        index = pickle.load(f)

    if not index.get("ids") or len(index.get("vectors", [])) == 0:
        print("Embeddings index is empty. Run `python link.py` first.")
        return

    print(f"Embedding search query: '{query}'...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    query_vector = model.encode(query).reshape(1, -1)
    
    vectors = index["vectors"]
    if isinstance(vectors, list):
        vectors = np.vstack(vectors)

    similarities = cosine_similarity(query_vector, vectors)[0]
    
    # Sort indices by score
    sorted_indices = np.argsort(similarities)[::-1][:top_k]
    
    note_dict = {n["id"]: n for n in notes}
    
    print(f"\nTop {top_k} semantic matches for '{query}':\n")
    for idx in sorted_indices:
        note_id = index["ids"][idx]
        score = similarities[idx]
        n = note_dict.get(note_id)
        if n:
            print(f"Score: {score:.4f} | [{n['category']}] {n['title']}")
            print(f"  ID:      {n['id']}")
            print(f"  Tags:    {', '.join(n['tags'])}")
            if n['summary']:
                print(f"  Summary: {n['summary']}")
            print()


def main() -> None:
    parser = argparse.ArgumentParser(description="SecondSelf CLI Search & List Tool")
    parser.add_argument("query", nargs="?", help="Keyword or semantic search query")
    parser.add_argument("-l", "--list", action="store_true", help="List all notes")
    parser.add_argument("-t", "--tag", help="Filter notes by tag")
    parser.add_argument("-c", "--category", help="Filter notes by PARA category (Projects, Areas, Resources, Archives)")
    parser.add_argument("-s", "--semantic", action="store_true", help="Perform semantic vector search using ML embeddings")

    args = parser.parse_args()
    
    notes = load_all_wiki_notes()
    
    if args.list or (not args.query and not args.tag and not args.category):
        list_notes(notes, tag_filter=args.tag, category_filter=args.category)
    elif args.semantic and args.query:
        semantic_search(notes, args.query)
    elif args.query:
        keyword_search(notes, args.query)
    elif args.tag or args.category:
        list_notes(notes, tag_filter=args.tag, category_filter=args.category)


if __name__ == "__main__":
    main()
