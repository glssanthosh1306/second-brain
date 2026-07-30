"""Shared paths and constants for SecondSelf."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "raw"
WIKI_DIR = ROOT / "wiki"
DATA_DIR = ROOT / "data"
STATIC_DIR = ROOT / "static"
GRAPH_JSON = DATA_DIR / "graph.json"
EMBEDDINGS_PATH = WIKI_DIR / ".index" / "embeddings.pkl"
NOTE_REGISTRY = WIKI_DIR / ".index" / "note_registry.json"

PARA_FOLDERS = ["Projects", "Areas", "Resources", "Archives"]
SIMILARITY_THRESHOLD = 0.75
TOP_K_LINKS = 5
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

MIN_PYTHON_VERSION = (3, 10)


def check_python_version() -> None:
    if sys.version_info < MIN_PYTHON_VERSION:
        major, minor = MIN_PYTHON_VERSION
        current = sys.version.split()[0]
        raise RuntimeError(
            f"SecondSelf requires Python {major}.{minor}+ (found {current})."
        )


def ensure_project_dirs() -> None:
    """Create required folders if they do not exist."""
    dirs = [
        RAW_DIR,
        DATA_DIR,
        STATIC_DIR,
        WIKI_DIR / ".index",
        *(WIKI_DIR / folder for folder in PARA_FOLDERS),
    ]
    for path in dirs:
        path.mkdir(parents=True, exist_ok=True)


def bootstrap() -> None:
    """Validate environment and ensure project layout exists."""
    check_python_version()
    ensure_project_dirs()


if __name__ == "__main__":
    bootstrap()
    print("SecondSelf bootstrap OK")
    print(f"  ROOT:       {ROOT}")
    print(f"  Python:     {sys.version.split()[0]}")
    print(f"  raw/:       {RAW_DIR.exists()}")
    print(f"  wiki/:      {WIKI_DIR.exists()}")
    print(f"  PARA dirs:  {all((WIKI_DIR / f).exists() for f in PARA_FOLDERS)}")
