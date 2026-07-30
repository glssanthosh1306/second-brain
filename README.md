# SecondSelf — Your Personal AI Second Brain

Build an end-to-end system where you can capture *anything* (a note, a link, a file), have AI automatically classify and file it, auto-link it to related knowledge, render it as a live interactive graph you can explore, and ask it any question in plain English to get an answer synthesized from your own accumulated knowledge.

> Not a notes app. Not a chatbot. A brain that organizes itself and answers for you.

## Pipeline

```
Capture → Classify → Link → Graph → Ask → Deploy
```

## Requirements

- Python 3.10+
- [Groq API key](https://console.groq.com/) (Phase 2+)

## Setup

```bash
# Clone the repo and enter the project directory
cd secondself

# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure secrets (Phase 2+)
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
# Edit .env and set GROQ_API_KEY

# Verify bootstrap (creates folders, checks Python version)
python config.py
```

## Project Structure

```text
secondself/
├── raw/                  # Raw captures (timestamp + unique ID)
├── wiki/                 # Classified, linked notes (PARA folders)
├── data/                 # graph.json and derived data
├── static/               # Graph UI assets
├── docs/                 # Architecture, implementation plan, edge cases
├── config.py             # Shared paths and constants
├── capture.py            # Phase 1 — capture pipeline
├── classify.py           # Phase 2 — PARA classification
├── link.py               # Phase 2 — embedding auto-links
├── build_graph.py        # Phase 3 — graph JSON builder
├── ask.py                # Phase 4 — RAG Q&A
├── app.py                # Phase 4 — Streamlit UI
└── requirements.txt
```

## Phase Roadmap

| Phase | Name | Status |
|-------|------|--------|
| 0 | Project Bootstrap | Done |
| 1 | The Archivist — Capture pipeline | Pending |
| 2 | The Librarian — Classify + link | Pending |
| 3 | The Cartographer — Interactive graph | Pending |
| 4 | The Oracle — RAG + Streamlit deploy | Pending |

## Documentation

- [Problem Statement](docs/Problem_Statement.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Implementation Plan](docs/implementation-plan.md)
- [Edge Cases](docs/edge-case.md)

## License

MIT (or your chosen license)
