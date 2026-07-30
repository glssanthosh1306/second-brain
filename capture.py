"""SecondSelf — Capture Pipeline (Phase 1: The Archivist)

One CLI command captures notes, URLs, or local files into the raw/ inbox
with a unique timestamped ID and metadata.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from config import RAW_DIR, ensure_project_dirs

try:
    import pypdf
except ImportError:
    pypdf = None


@dataclass
class CaptureMetadata:
    id: str
    timestamp: str
    type: str  # 'note' | 'link' | 'file'
    source: str  # 'cli'
    original_filename: Optional[str]
    content_path: str


def generate_capture_id() -> str:
    """Generate a unique ID in format YYYYMMDD_HHMMSS_6charuuid."""
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:6]
    return f"{timestamp_str}_{short_uuid}"


def get_iso_timestamp() -> str:
    """Return local timestamp in ISO 8601 format with timezone."""
    return datetime.now().astimezone().isoformat()


def write_meta(capture_dir: Path, meta: CaptureMetadata) -> Path:
    """Serialize and write meta.json inside the capture folder."""
    meta_file = capture_dir / "meta.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(asdict(meta), f, indent=2, ensure_ascii=False)
    return meta_file


def capture_note(text: str, source: str = "cli") -> str:
    """Capture a plain-text or markdown note."""
    ensure_project_dirs()
    capture_id = generate_capture_id()
    capture_dir = RAW_DIR / capture_id
    capture_dir.mkdir(parents=True, exist_ok=True)

    content_file = capture_dir / "content.md"
    content_file.write_text(text.strip() + "\n", encoding="utf-8")

    meta = CaptureMetadata(
        id=capture_id,
        timestamp=get_iso_timestamp(),
        type="note",
        source=source,
        original_filename=None,
        content_path="content.md",
    )
    write_meta(capture_dir, meta)

    return capture_id


def capture_link(url: str, source: str = "cli") -> str:
    """Capture a URL, optionally fetching page title and description."""
    ensure_project_dirs()
    capture_id = generate_capture_id()
    capture_dir = RAW_DIR / capture_id
    capture_dir.mkdir(parents=True, exist_ok=True)

    title = ""
    excerpt = ""
    fetch_success = False

    # Attempt to fetch page metadata
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            html = resp.text
            # Simple title extraction
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()

            # Simple meta description extraction
            desc_match = re.search(
                r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
                html,
                re.IGNORECASE,
            )
            if not desc_match:
                desc_match = re.search(
                    r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']',
                    html,
                    re.IGNORECASE,
                )
            if desc_match:
                excerpt = desc_match.group(1).strip()

            fetch_success = True
    except Exception as e:
        # Request failed; store raw URL without failing capture
        pass

    display_title = title if title else url
    md_content = f"# {display_title}\n\nURL: {url}\n"
    if excerpt:
        md_content += f"\n> {excerpt}\n"
    if not fetch_success:
        md_content += "\n*(Metadata fetch omitted or failed during capture)*\n"

    content_file = capture_dir / "content.md"
    content_file.write_text(md_content, encoding="utf-8")

    meta = CaptureMetadata(
        id=capture_id,
        timestamp=get_iso_timestamp(),
        type="link",
        source=source,
        original_filename=None,
        content_path="content.md",
    )
    write_meta(capture_dir, meta)

    return capture_id


def capture_file(file_path_str: str, source: str = "cli") -> str:
    """Capture a local file (copying it into raw/ and extracting text where possible)."""
    ensure_project_dirs()
    src_path = Path(file_path_str).resolve()
    if not src_path.exists() or not src_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path_str}")

    capture_id = generate_capture_id()
    capture_dir = RAW_DIR / capture_id
    capture_dir.mkdir(parents=True, exist_ok=True)

    dest_filename = src_path.name
    dest_path = capture_dir / dest_filename
    shutil.copy2(src_path, dest_path)

    extracted_text = ""
    suffix = src_path.suffix.lower()

    # If PDF, attempt text extraction via pypdf
    if suffix == ".pdf":
        if pypdf is not None:
            try:
                reader = pypdf.PdfReader(str(dest_path))
                pages_text = []
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    pages_text.append(f"--- Page {i+1} ---\n{text}")
                extracted_text = "\n\n".join(pages_text)
            except Exception as e:
                extracted_text = f"[PDF Text Extraction Failed: {e}]"
        else:
            extracted_text = "[pypdf not installed. Original PDF copied.]"

    # If plain text / markdown / code file, read directly
    elif suffix in [".txt", ".md", ".py", ".json", ".csv", ".yaml", ".yml", ".html"]:
        try:
            extracted_text = src_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            extracted_text = ""

    content_path = dest_filename
    if extracted_text.strip():
        content_file = capture_dir / "content.md"
        content_file.write_text(
            f"# File: {dest_filename}\n\n" + extracted_text, encoding="utf-8"
        )
        content_path = "content.md"

    meta = CaptureMetadata(
        id=capture_id,
        timestamp=get_iso_timestamp(),
        type="file",
        source=source,
        original_filename=dest_filename,
        content_path=content_path,
    )
    write_meta(capture_dir, meta)

    return capture_id


def capture(input_type: str, content: str, source: str = "cli") -> str:
    """Unified capture function routing to note, link, or file handlers."""
    if input_type == "note":
        return capture_note(content, source=source)
    elif input_type == "link":
        return capture_link(content, source=source)
    elif input_type == "file":
        return capture_file(content, source=source)
    else:
        raise ValueError(f"Unknown capture type: {input_type}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SecondSelf — Capture notes, links, or files into raw inbox."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--note", type=str, help="Capture a plain text note")
    group.add_argument("--link", type=str, help="Capture a URL")
    group.add_argument("--file", type=str, help="Capture a local file (path)")

    args = parser.parse_args()

    try:
        if args.note:
            cid = capture_note(args.note)
            print(f"Captured note [ID: {cid}] -> raw/{cid}/")
        elif args.link:
            cid = capture_link(args.link)
            print(f"Captured link [ID: {cid}] -> raw/{cid}/")
        elif args.file:
            cid = capture_file(args.file)
            print(f"Captured file [ID: {cid}] -> raw/{cid}/")
    except Exception as err:
        print(f"Error capturing input: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
