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

## Usage

```bash
# 1. Capture anything (note, link, or file)
python capture.py --note "Idea about RAG pipelines"
python capture.py --link "https://example.com/article"
python capture.py --file "./document.pdf"

# 2. Run the processing pipeline (classify -> link -> build_graph)
python pipeline.py

# 3. Ask your brain questions in CLI
python ask.py "What have I captured about machine learning?"

# 4. Launch the Streamlit Web Application
streamlit run app.py
```

## Phase Roadmap

| Phase | Name | Status |
|-------|------|--------|
| 0 | Project Bootstrap | Completed 🏆 |
| 1 | The Archivist — Capture pipeline (`capture.py`) | Completed 🏆 |
| 2 | The Librarian — Classify + link (`classify.py`, `link.py`) | Completed 🏆 |
| 3 | The Cartographer — Interactive graph (`build_graph.py`) | Completed 🏆 |
| 4 | The Oracle — RAG + Streamlit UI (`ask.py`, `app.py`, `pipeline.py`) | Completed 🏆 |

## Documentation

- [Problem Statement](docs/Problem_Statement.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Implementation Plan](docs/implementation-plan.md)
- [Deployment Plan](docs/deployment-plan.md)
- [Edge Cases](docs/edge-case.md)

## License

MIT

