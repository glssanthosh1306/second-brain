# SecondSelf — Edge Cases & Corner Scenarios

This document catalogs known edge cases, corner scenarios, and failure modes for **SecondSelf**. Use it during implementation and testing to ensure each pipeline stage handles messy real-world input gracefully.

**Related documents:**
- [ARCHITECTURE.md](./ARCHITECTURE.md) — System design and data models
- [implementation-plan.md](./implementation-plan.md) — Phase-wise build guide

**Severity legend:**

| Level | Meaning |
|-------|---------|
| 🔴 Critical | Can corrupt data, crash the app, or leak secrets — must handle before ship |
| 🟠 High | Breaks a core feature or produces misleading output — handle in MVP |
| 🟡 Medium | Degrades UX or requires manual recovery — handle if time allows |
| 🟢 Low | Rare or cosmetic — document and defer |

---

## How to Use This Document

1. **During implementation** — Check the section for your current phase before marking it complete.
2. **During testing** — Pick 2–3 edge cases per phase and verify expected behavior.
3. **When bugs appear** — Add new scenarios here with date and resolution notes.
4. **Before deployment** — Review 🔴 Critical and 🟠 High items in Phases 4 and Cross-Pipeline sections.

---

## Phase 0 — Project Bootstrap

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| P0-01 | `raw/` or `wiki/` folder missing | 🔴 | Scripts fail on first run | Auto-create directories in `config.py` startup or each module's init |
| P0-02 | Python version < 3.10 | 🟠 | Syntax/type hint errors | Document minimum version in README; check at startup |
| P0-03 | Running scripts from wrong working directory | 🟠 | Paths resolve to wrong location | Use `Path(__file__).parent` in `config.py`, never relative CWD assumptions |
| P0-04 | `.env` file missing | 🟠 | Groq calls fail in Phase 2+ | Fail with clear message: "Set GROQ_API_KEY in .env" |
| P0-05 | `.env` committed to git | 🔴 | API key exposed publicly | `.gitignore` + pre-commit check; rotate key if leaked |
| P0-06 | PARA subfolders partially created | 🟡 | Classify writes to non-existent folder | Create all four PARA folders on bootstrap |
| P0-07 | Windows vs Unix path separators | 🟡 | Broken paths on cross-platform use | Always use `pathlib.Path`, never string concatenation |
| P0-08 | Repo cloned on machine without write permissions | 🟡 | Capture fails silently or with OS error | Surface permission error with folder path |
| P0-09 | Duplicate `config.py` in root and `src/` | 🟡 | Inconsistent constants across modules | Single source of truth — one config module only |
| P0-10 | `requirements.txt` version conflicts | 🟠 | Install or runtime failures | Pin versions after first successful install |

---

## Phase 1 — Capture Pipeline (`capture.py`)

### Input & Content Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| C-01 | Empty note (`--note ""`) | 🟠 | Reject or capture with warning | Validate non-empty after strip; exit code 1 with message |
| C-02 | Note with only whitespace | 🟠 | Same as empty note | Strip before validation |
| C-03 | Very long note (100K+ characters) | 🟡 | Capture succeeds; may truncate in LLM later | Store full content in raw; truncate only at classify prompt (with note in meta) |
| C-04 | Note with special characters (emoji, CJK, RTL) | 🟡 | Capture and store as UTF-8 | Write files with `encoding="utf-8"`; no ASCII-only assumptions |
| C-05 | Note containing YAML frontmatter delimiters (`---`) | 🟡 | Raw stored correctly; classify may confuse parser | Store as-is in raw; escape or wrap when building wiki frontmatter |
| C-06 | Note with null bytes or binary content pasted | 🟡 | Capture may corrupt file | Strip `\x00` from text input; reject if binary detected |
| C-07 | Multiline note via CLI quoting issues (Windows PowerShell) | 🟡 | Partial or broken capture | Document quoting; support `--note-file path.txt` as alternative |
| C-08 | Note from stdin pipe | 🟢 | Optional enhancement | `echo "text" \| python capture.py --stdin` (future) |

### Link Capture Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| C-10 | Invalid URL format | 🟠 | Reject with validation error | Validate scheme (`http`/`https`) and basic URL structure |
| C-11 | URL without protocol (`example.com`) | 🟡 | Auto-prepend `https://` or reject | Prepend `https://` with logged assumption |
| C-12 | URL returns 404 / 500 | 🟡 | Capture URL anyway; store status in meta | Save URL + HTTP status; optional `fetch_error` in meta.json |
| C-13 | URL timeout or DNS failure | 🟡 | Capture URL without fetched content | Set `fetch_status: "failed"` in meta; store URL only |
| C-14 | URL to large page (multi-MB HTML) | 🟡 | Don't store full HTML | Extract title + first N chars excerpt only |
| C-15 | URL requiring authentication (paywall, login) | 🟡 | Capture URL; minimal content | Store URL + "auth required" note in content.md |
| C-16 | Redirect chains (301/302) | 🟢 | Follow redirects; store final URL | Use `requests` with `allow_redirects=True`; record final URL |
| C-17 | `javascript:` or `file:` URLs | 🔴 | Reject — security risk | Block non-http(s) schemes |
| C-18 | Duplicate link captured twice | 🟢 | Two separate captures (append-only) | Allowed by design; dedup is a future feature |
| C-19 | URL with tracking query params | 🟢 | Store as provided | Optional: strip UTM params before fetch |

### File Capture Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| C-20 | File path does not exist | 🟠 | Clear error, no partial capture | Validate path before copy; exit code 1 |
| C-21 | File path is a directory | 🟠 | Reject | Check `path.is_file()` |
| C-22 | Very large file (>50 MB) | 🟡 | Warn or reject | Configurable `MAX_FILE_SIZE_MB`; reject with message |
| C-23 | PDF with scanned images (no text layer) | 🟠 | Capture file; empty text extraction | Store PDF; set `text_extracted: false` in meta |
| C-24 | Password-protected PDF | 🟡 | Capture file; extraction fails gracefully | Catch pypdf encryption error; note in meta |
| C-25 | Corrupt or malformed PDF | 🟡 | Capture binary; skip text extraction | Try/except around pypdf; log warning |
| C-26 | Image file (PNG, JPG) — no text | 🟡 | Capture binary; empty or OCR-skipped content | Store file; content.md notes "image capture, no text" |
| C-27 | Filename with special chars (`report (1).pdf`) | 🟡 | Sanitize stored filename | Preserve original in meta; sanitize copy filename |
| C-28 | Filename collision in same capture folder | 🟢 | Unlikely (folder-per-capture) | UUID folder prevents collisions |
| C-29 | Symlink as file path | 🟡 | Follow or reject symlink | Resolve real path; optionally reject symlinks for security |
| C-30 | Path traversal attempt (`../../etc/passwd`) | 🔴 | Reject | Resolve path; ensure result is under allowed directory |
| C-31 | Unsupported file type (.exe, .zip) | 🟡 | Capture binary without extraction | Copy file; note type in meta; no execution |
| C-32 | File on network drive disconnects mid-copy | 🟡 | Fail cleanly; no orphan folder | Write to temp; move atomically on success |
| C-33 | Disk full during capture | 🔴 | Fail with OS error; no corrupt meta | Write meta.json last, after content is saved |

### ID & Metadata Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| C-40 | Two captures in same second — ID collision | 🟡 | UUID suffix prevents collision | Use UUID4 (or 6+ char hex), not timestamp alone |
| C-41 | System clock wrong or changes (DST, timezone) | 🟢 | Timestamp reflects local TZ | Use `datetime.now(timezone.utc)` or explicit local TZ in meta |
| C-42 | `meta.json` written but content write fails | 🔴 | Orphan or inconsistent capture | Write content first; write meta.json last (atomic finalize) |
| C-43 | Partial capture folder from crashed run | 🟡 | Detect and skip or repair | Validate meta.json + content_path exist before processing |
| C-44 | Manual edits to `raw/` by user | 🟡 | Pipeline may break on invalid meta | Validate schema in classify; skip invalid with log |
| C-45 | Multiple CLI flags at once (`--note` and `--file`) | 🟠 | Reject ambiguous input | Mutually exclusive argparse group |
| C-46 | No CLI flags provided | 🟠 | Print usage and exit | argparse handles via `required=True` or custom check |

---

## Phase 2 — Classification (`classify.py`)

### Raw Input & Processing Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| CL-01 | Empty or whitespace-only capture content | 🟠 | Skip or classify as Archives with tag `empty` | Skip with log, or minimal default classification |
| CL-02 | Capture folder missing `meta.json` | 🟡 | Skip with warning | Validate before processing |
| CL-03 | Capture folder missing content file | 🟡 | Skip with warning | Check `content_path` exists |
| CL-04 | Invalid JSON in `meta.json` | 🟡 | Skip capture; log error | try/except on load |
| CL-05 | Unknown `type` in meta (`"unknown"`) | 🟡 | Attempt classify on whatever content exists | Treat as generic note |
| CL-06 | Re-running classify on already-processed capture | 🟠 | No duplicate wiki notes | Check processed marker or existing wiki ID |
| CL-07 | Processed marker set but wiki note deleted | 🟡 | Re-classify or warn | Option: re-process if wiki note missing |
| CL-08 | Capture content exceeds LLM context window | 🟠 | Truncate with indicator | Take first N tokens/chars; append "[truncated]" to prompt |
| CL-09 | Non-English content | 🟡 | Classify in original language | LLM handles multilingual; tags may be mixed language |
| CL-10 | Content is only a URL with no fetched body | 🟡 | Classify from URL string | Use URL + domain as classification input |
| CL-11 | Binary file with no extracted text | 🟡 | Classify from filename + type | Prompt includes filename and file type |
| CL-12 | Concurrent classify runs (double-click pipeline) | 🟠 | Race on same captures | File lock or processed marker before API call |

### LLM Response Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| CL-20 | LLM returns invalid JSON | 🟠 | Retry up to 2 times | Strip markdown fences; regex extract JSON object |
| CL-21 | LLM wraps JSON in code block | 🟠 | Parse successfully after strip | Remove ` ```json ` and ` ``` ` |
| CL-22 | LLM returns valid JSON but wrong schema | 🟠 | Retry or use defaults | Validate required keys: `para`, `tags`, `summary` |
| CL-23 | LLM returns invalid PARA value (`"Tasks"`) | 🟠 | Map to closest or default to Resources | Allowlist: Projects, Areas, Resources, Archives |
| CL-24 | LLM returns empty tags array | 🟡 | Accept; wiki note has no tags | Optional: generate tag from summary keywords |
| CL-25 | LLM returns 50+ tags | 🟡 | Truncate to top 10 | Cap tag count in validation |
| CL-26 | Summary exceeds one line (paragraph) | 🟡 | Truncate to ~200 chars | Truncate for frontmatter and graph label |
| CL-27 | Summary contains quotes breaking YAML | 🟡 | Valid frontmatter | Use `python-frontmatter` library; quote-escape strings |
| CL-28 | Groq API rate limit (429) | 🟠 | Retry with exponential backoff | sleep(2^n); max 3 retries |
| CL-29 | Groq API key missing or invalid | 🔴 | Fail fast with clear message | Check env at startup |
| CL-30 | Groq API timeout or 5xx | 🟠 | Retry; skip capture on persistent failure | Log failed capture IDs for manual retry |
| CL-31 | Groq model deprecated or renamed | 🟡 | API error | Configurable model name in config.py |
| CL-32 | LLM hallucinates category unrelated to content | 🟡 | Accept (user can re-file later) | Document limitation; future: confidence score |
| CL-33 | Network offline during classify batch | 🟠 | Partial batch completes | Process one-at-a-time; mark only successful ones processed |

### Wiki Write Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| CL-40 | Slug collision (two notes → same filename) | 🟠 | Second file overwrites first | Append capture ID suffix to slug: `summary-a1b2c3.md` |
| CL-41 | Summary produces empty slug after sanitization | 🟡 | Fallback slug | Use capture ID as filename |
| CL-42 | Summary contains `/` or `\` (path chars) | 🟠 | Sanitize slug | Replace path separators with `-` |
| CL-43 | Note moved between PARA folders on re-classify | 🟡 | Old file orphaned | Delete old wiki path if re-processing (careful with links) |
| CL-44 | YAML frontmatter parse error on write | 🟠 | Don't write corrupt file | Use library; validate round-trip parse |
| CL-45 | Disk full during wiki write | 🔴 | Fail; don't mark processed | Transaction-like: write wiki before marking processed |

---

## Phase 2 — Auto-Linking (`link.py`)

### Embedding Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| L-01 | Empty note body (only frontmatter) | 🟡 | Embed summary or skip | Fallback: embed `summary` field |
| L-02 | Very short note ("ok", "yes") | 🟡 | Weak embeddings; spurious links | Raise threshold for notes under N chars |
| L-03 | Identical duplicate notes | 🟡 | High similarity → linked | Expected; optional dedup in future |
| L-04 | First note in wiki (no others to link) | 🟢 | Empty links array | Skip comparison; add to index only |
| L-05 | Embedding model download fails (offline) | 🟠 | Clear error on first run | Cache model locally; document manual download |
| L-06 | Embedding model version changed | 🟠 | Stale index incompatible | Store model name in index; rebuild if mismatch |
| L-07 | `embeddings.pkl` corrupted | 🟡 | Rebuild from wiki | Detect load failure; trigger full re-index |
| L-08 | Note ID in index but wiki file deleted | 🟡 | Orphan vector | Rebuild index from wiki scan; prune orphans |
| L-09 | Wiki note exists but not in index | 🟠 | Missing from similarity search | Incremental index update on link run |
| L-10 | Embedding vector is all zeros (model error) | 🟡 | Skip or re-embed | Validate vector norm > 0 |

### Similarity & Linking Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| L-20 | Threshold too low → everything links to everything | 🟠 | Cluttered graph | Tune threshold; cap TOP_K at 5 |
| L-21 | Threshold too high → no links at all | 🟡 | Isolated nodes | Document tuning; suggest 0.72–0.80 range |
| L-22 | Self-link (note matches itself) | 🟠 | Never link to self | Exclude same ID from comparison |
| L-23 | Bidirectional update partial failure | 🟡 | One-way link only | Update both notes in same pass; log asymmetry |
| L-24 | Link to non-existent note ID in frontmatter | 🟡 | Broken graph edge | Validate target IDs exist during link or graph build |
| L-25 | Circular links (A→B, B→A) | 🟢 | Two edges in graph | Deduplicate edges in build_graph |
| L-26 | Re-run link.py clears existing manual links | 🟠 | Preserve or merge links | Merge new auto-links with existing; don't overwrite manual |
| L-27 | Notes in different languages linked incorrectly | 🟡 | Possible false positives | Lower confidence; multilingual model helps |
| L-28 | Hub note (generic "ideas" note) links to everything | 🟡 | Over-connected node | Cap links; exclude notes with generic summaries |
| L-29 | Concurrent link runs corrupt pickle index | 🟠 | Index corruption | File lock during save; atomic write (temp + rename) |
| L-30 | TOP_K links have identical similarity scores | 🟢 | Arbitrary order acceptable | Stable sort by ID for reproducibility |

---

## Phase 3 — Graph Builder & Visualization

### Graph Build Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| G-01 | Empty wiki (no notes) | 🟡 | Empty graph JSON `{nodes:[], edges:[]}` | Export valid empty graph; UI shows empty state |
| G-02 | Single note, no links | 🟢 | One node, zero edges | Valid graph; render single node |
| G-03 | Wiki note missing required frontmatter fields | 🟡 | Skip or use defaults | Default `para: Resources`, `label: "Untitled"` |
| G-04 | Duplicate note IDs across PARA folders | 🟠 | Graph merge conflict | Last wins or error; enforce unique IDs at classify |
| G-05 | `links` field is string instead of list | 🟡 | Parse or skip | Coerce single string to list; log warning |
| G-06 | Edge points to missing node ID | 🟡 | Skip orphan edge | Filter edges where source and target exist in nodes |
| G-07 | Markdown file in wiki root (not in PARA folder) | 🟡 | Include or ignore | Scan all `wiki/**/*.md` except `.index/` |
| G-08 | `.index/` or hidden files scanned as notes | 🟡 | Exclude | Glob exclude `wiki/.index/**` |
| G-09 | Invalid UTF-8 in note body | 🟡 | Skip or replace errors | `errors="replace"` on read |
| G-10 | `content_preview` with newlines breaks JSON | 🟡 | Valid JSON export | Escape newlines; truncate to 200 chars |
| G-11 | Special characters in label break vis-network | 🟡 | Render correctly | JSON-escape; HTML-escape in tooltip |
| G-12 | graph.json write fails mid-serialization | 🟡 | Corrupt JSON file | Write to temp file; atomic rename |
| G-13 | Stale graph.json (wiki updated, graph not rebuilt) | 🟠 | Outdated visualization | Document rebuild step; pipeline button in app |

### Interactive Graph UI Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| G-20 | graph.json missing | 🟠 | UI shows message, not crash | "Run build_graph.py first" empty state |
| G-21 | graph.json invalid JSON | 🟠 | Graceful error in Streamlit | try/except on load; show error banner |
| G-22 | 100+ nodes — performance degradation | 🟡 | Slow physics simulation | Limit physics iterations; cluster or filter by PARA |
| G-23 | 500+ nodes — browser tab freeze | 🟡 | Unusable graph | Pagination/filter UI; warn in docs |
| G-24 | Node label too long for display | 🟢 | Truncate in canvas | Truncate label to ~30 chars; full text on hover |
| G-25 | Hover popup with very long content | 🟡 | Scrollable or truncated tooltip | Cap preview length in tooltip |
| G-26 | All nodes same PARA category — no color variety | 🟢 | All one color | Acceptable; legend still works |
| G-27 | vis-network CDN blocked (offline/corporate firewall) | 🟡 | Graph doesn't render | Bundle vis-network locally in `static/` |
| G-28 | Streamlit iframe height too small | 🟢 | Graph clipped | Set `height=600` minimum in `st.components.v1.html` |
| G-29 | User clicks node — sidebar note missing | 🟡 | "Note not found" message | Lookup by ID; handle missing file |
| G-30 | Graph rendered before JSON loaded (race) | 🟡 | Loading spinner | Show spinner until graph data ready |

---

## Phase 4 — RAG / Ask (`ask.py`)

### Query Input Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| A-01 | Empty question string | 🟠 | Reject with prompt | Validate non-empty before embed/API call |
| A-02 | Question with only whitespace | 🟠 | Reject | Strip and validate |
| A-03 | Very long question (10K chars) | 🟡 | Truncate for embedding | Embed first N chars |
| A-04 | Question in different language than notes | 🟡 | Retrieve may be weak | Multilingual embedding model; note limitation |
| A-05 | Question with prompt injection ("Ignore instructions...") | 🟠 | Grounded answer only | System prompt: answer ONLY from notes |
| A-06 | Question unrelated to any captured content | 🟡 | Honest "insufficient information" | Low retrieval scores → skip LLM or explicit no-info response |
| A-07 | Ambiguous question ("Tell me about it") | 🟡 | Best-effort or ask to clarify | Return top matches with low confidence note |
| A-08 | Question asking for real-time data ("Today's weather") | 🟡 | Not in notes — say so | Grounded prompt prevents fabrication |

### Retrieval Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| A-10 | Empty embedding index (no notes processed) | 🟠 | Clear message | "No notes indexed yet. Run classify and link first." |
| A-11 | All retrieval scores below threshold | 🟡 | No context → honest answer | Set min score threshold; don't call LLM with empty context |
| A-12 | Top-K retrieval returns duplicate notes | 🟢 | Dedupe in context | Dedupe by note ID before building prompt |
| A-13 | Retrieved notes contradict each other | 🟡 | LLM acknowledges conflict | Prompt: note contradictions if present |
| A-14 | Retrieved note body truncated in context | 🟡 | Partial answer | Include full body up to context limit; prioritize by score |
| A-15 | Stale index — new notes not searchable | 🟠 | Missing recent content | Rebuild index on pipeline refresh; document |
| A-16 | Question matches note title but not body | 🟡 | May still retrieve via embedding | Embedding covers summary + body |
| A-17 | Single note wiki — always retrieved | 🟢 | Works correctly | Valid RAG with one source |

### LLM Synthesis Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| A-20 | LLM hallucinates facts not in notes | 🟠 | Minimize via grounding | Strict prompt; show source IDs; user verifies |
| A-21 | LLM ignores "only use provided notes" instruction | 🟠 | Possible fabrication | Lower temperature; cite-or-silent prompt |
| A-22 | LLM returns empty answer | 🟡 | Fallback message | "Unable to generate answer. Try rephrasing." |
| A-23 | Context window exceeded (many long notes) | 🟠 | Truncate context | Limit total context chars; top-K by score |
| A-24 | Groq rate limit during ask | 🟠 | Retry with backoff | Same as classify 429 handling |
| A-25 | Source IDs cited don't match retrieved notes | 🟡 | Mismatch in citations | Validate cited IDs against retrieval set |
| A-26 | Answer correct but sources list empty | 🟡 | Always return sources | Map retrieval scores to source list programmatically |
| A-27 | User asks for sensitive content from notes | 🟡 | Answer shown in UI | Document privacy for public deploy |

---

## Phase 4 — Streamlit App (`app.py`)

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| UI-01 | App starts with no `data/graph.json` | 🟠 | Empty graph state, app loads | Don't crash; show setup instructions |
| UI-02 | App starts with no embeddings | 🟠 | Ask fails gracefully | Message in ask panel |
| UI-03 | User spams Ask button | 🟡 | Rate limit or disable during load | Disable button while `st.spinner` active |
| UI-04 | Pipeline refresh runs during ask query | 🟡 | Race on index files | Disable refresh while ask in progress |
| UI-05 | Capture form in sidebar with empty input | 🟠 | Validation error | Same rules as CLI capture |
| UI-06 | Streamlit session rerun clears graph state | 🟢 | Graph re-renders | Expected Streamlit behavior |
| UI-07 | Multiple browser tabs on same app | 🟡 | Concurrent pipeline triggers | File lock on index writes |
| UI-08 | `@st.cache_data` serves stale graph | 🟠 | Old graph after rebuild | Cache key includes graph.json mtime |
| UI-09 | HTML graph component XSS via note content | 🔴 | No script execution | Escape user content in tooltips |
| UI-10 | File upload exceeds Streamlit limit | 🟡 | Upload error | Document max size; match capture.py limit |

---

## Phase 4 — Deployment

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| D-01 | `GROQ_API_KEY` not set in Streamlit secrets | 🔴 | Ask/classify fail in cloud | Check at startup; show config error in UI |
| D-02 | Cold start > 60s (model download) | 🟠 | User sees long blank screen | Pre-commit embeddings; lazy load with progress |
| D-03 | `sentence-transformers` OOM on free tier | 🟠 | App crash on first ask | Smaller model; pre-baked embeddings only |
| D-04 | Repo contains private notes publicly | 🔴 | Data leak | Sanitized demo wiki; `.gitignore` personal data |
| D-05 | `requirements.txt` unpinned — build breaks | 🟠 | Deploy failure | Pin versions after local success |
| D-06 | App sleeps on free tier (Streamlit idle) | 🟡 | Slow wake on next visit | Expected; show loading state |
| D-07 | Git LFS embeddings too large for free tier | 🟡 | Clone/deploy fail | Exclude embeddings from repo; rebuild on deploy |
| D-08 | HF Spaces vs Streamlit Cloud path differences | 🟡 | Broken static paths | Use relative paths from config ROOT |
| D-09 | Deploy succeeds but graph empty (wiki not committed) | 🟠 | Empty demo | Commit demo `wiki/` + `graph.json` |
| D-10 | API key quota exhausted mid-demo | 🟡 | User-facing error | Friendly message; link to Groq dashboard |

---

## Cross-Pipeline & Data Integrity

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| X-01 | Run pipeline steps out of order (graph before classify) | 🟡 | Stale or empty output | Document order; pipeline.py enforces sequence |
| X-02 | Partial pipeline failure mid-batch | 🟠 | Some notes processed, some not | Per-item error handling; continue batch |
| X-03 | Manual edit to wiki frontmatter breaks parser | 🟡 | Skip note or use defaults | Robust frontmatter parsing with fallbacks |
| X-04 | Manual delete of wiki note — raw still marked processed | 🟡 | Ghost references in links | Periodic link validation; prune dead links |
| X-05 | Restore wiki from backup — index out of sync | 🟡 | Wrong retrieval results | Full re-run of link.py after restore |
| X-06 | Copy project folder — absolute paths break | 🟡 | Portable via config ROOT | Never hardcode absolute paths |
| X-07 | Two machines sync same repo via git — conflicting pickles | 🟠 | Corrupt index | Don't commit pickle; regenerate on each machine |
| X-08 | Capture ID referenced in links but raw deleted | 🟢 | Orphan edge | Prune on graph build |
| X-09 | Unicode normalization differences (é vs e + combining) | 🟢 | Possible missed links | NFC normalize before embed (optional) |
| X-10 | End-to-end test note pollutes real wiki | 🟢 | Test data in graph | Use identifiable prefix; delete after test |

---

## Security & Privacy Edge Cases

| ID | Scenario | Severity | Expected Behavior | Handling |
|----|----------|----------|-------------------|----------|
| S-01 | API key in error stack trace shown in Streamlit | 🔴 | Never expose secrets | Catch API errors; show generic message |
| S-02 | Note content sent to Groq (third party) | 🟠 | User informed | Document in README privacy section |
| S-03 | Public URL indexes search engines | 🟡 | Demo data only | robots.txt optional; no sensitive deploys |
| S-04 | Malicious file upload (polyglot PDF) | 🟡 | Store only; never execute | No shell execution; validate MIME loosely |
| S-05 | SSRF via link capture (internal IPs) | 🟠 | Block private IP ranges | Block `localhost`, `127.0.0.1`, `10.x`, `192.168.x` in fetch |
| S-06 | XSS in note rendered in graph tooltip | 🔴 | Escaped output | HTML-escape all user content in JS |
| S-07 | Path traversal in file capture from Streamlit | 🔴 | Reject | Same validation as CLI |
| S-08 | Pickle deserialization of untrusted embeddings.pkl | 🟡 | Local trust only | Only load own index; don't import untrusted pickles |

---

## Performance & Scale Edge Cases

| ID | Scenario | Scenario Threshold | Expected Behavior | Handling |
|----|----------|-------------------|-------------------|----------|
| SC-01 | Wiki grows to 100+ notes | ~100 | Link O(n²) slows down | Batch nightly; consider FAISS at 1000+ |
| SC-02 | Wiki grows to 1000+ notes | ~1000 | Pickle load slow; graph cluttered | Migrate to vector DB; graph filter UI |
| SC-03 | Single note > 50K tokens | Large doc | Classify/RAG truncate | Chunking (post-MVP) |
| SC-04 | graph.json > 5 MB | Many nodes | Slow Streamlit load | Compress preview fields; lazy node loading |
| SC-05 | Batch classify 100 captures | API limits | Hours-long run | Rate limit aware queue; progress bar |
| SC-06 | Memory spike loading sentence-transformers | ~500 MB RAM | OOM on low-memory VM | Pre-baked embeddings; no model load in cloud |

---

## Empty & Zero-State Scenarios

These are valid system states that must not crash any component:

| State | capture.py | classify.py | link.py | build_graph.py | ask.py | app.py |
|-------|------------|-------------|---------|----------------|--------|--------|
| Fresh install, no data | ✅ Works | ✅ No-op | ✅ No-op | ✅ Empty graph | ⚠️ "No notes" | ✅ Empty UI |
| raw/ populated, wiki/ empty | ✅ Works | ✅ Populates wiki | ✅ Indexes | ✅ Nodes appear | ✅ After index built | ✅ After pipeline |
| wiki/ populated, no links | ✅ Works | ✅ Skips processed | ✅ May find links | ✅ Nodes, no edges | ✅ Works | ✅ Sparse graph |
| graph.json missing | ✅ Works | ✅ Works | ✅ Works | ✅ Creates file | ✅ Works | ⚠️ Empty graph msg |
| embeddings.pkl missing | ✅ Works | ✅ Works | ✅ Rebuilds | ✅ Works | ⚠️ Rebuild prompt | ⚠️ Ask disabled msg |

---

## Recommended Test Matrix (Minimum)

Pick at least one scenario per phase before marking the phase complete:

| Phase | Must-Test Edge Cases |
|-------|---------------------|
| 1 | C-01 (empty note), C-10 (bad URL), C-20 (missing file), C-40 (rapid captures) |
| 2 | CL-20 (bad JSON), CL-23 (invalid PARA), CL-40 (slug collision), L-01 (empty body), L-22 (self-link) |
| 3 | G-01 (empty wiki), G-06 (orphan edge), G-20 (missing graph.json), G-02 (single node) |
| 4 | A-01 (empty question), A-06 (unrelated question), A-10 (empty index), A-20 (hallucination check), D-01 (missing API key) |
| Cross | X-01 (wrong pipeline order), S-06 (XSS in tooltip), UI-08 (stale cache) |

---

## Edge Case Resolution Log

Use this section to track discoveries during development:

| Date | ID | Found During | Resolution | Status |
|------|----|--------------|------------|--------|
| — | — | — | — | — |

---

## Quick Reference — Fail-Gracefully Principles

From [ARCHITECTURE.md](./ARCHITECTURE.md) design principles, every edge case should follow:

1. **Never crash silently** — log the error and continue the batch when possible.
2. **Never corrupt existing data** — write atomically; raw is append-only.
3. **Never invent content** — empty retrieval → honest "I don't know".
4. **Never expose secrets** — generic error messages in UI.
5. **Always validate before external calls** — save API quota and user trust.

---

*Last updated: project planning phase. Add new rows to the Resolution Log as edge cases are discovered and fixed during implementation.*
