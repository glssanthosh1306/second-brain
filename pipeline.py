"""SecondSelf — Phase 2 Pipeline Runner

This script provides a simple entry‑point to execute the full Phase 2 pipeline:
1️⃣ Classify raw captures into structured wiki notes (classify.py)
2️⃣ Generate embeddings and auto‑link notes (link.py)

Running the pipeline ensures the two steps are performed in the correct order and any
errors are reported clearly.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Project root – assume this file lives in the repository root
ROOT = Path(__file__).resolve().parent

def run_classify(force: bool = False) -> int:
    """Execute classify.py.
    Returns the subprocess exit code.
    """
    cmd = [sys.executable, str(ROOT / "classify.py")]
    if force:
        cmd.append("--force")
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("Error during classification:", result.stderr, file=sys.stderr)
    return result.returncode


def run_link() -> int:
    """Execute link.py.
    Returns the subprocess exit code.
    """
    cmd = [sys.executable, str(ROOT / "link.py")]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("Error during linking:", result.stderr, file=sys.stderr)
    return result.returncode


def run_build_graph() -> int:
    """Execute build_graph.py.
    Returns the subprocess exit code.
    """
    cmd = [sys.executable, str(ROOT / "build_graph.py")]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("Error during graph building:", result.stderr, file=sys.stderr)
    return result.returncode


def run_full_pipeline(force_classify: bool = False) -> int:
    """Run classify -> link -> build_graph.
    Returns 0 on success or non-zero exit code.
    """
    code = run_classify(force=force_classify)
    if code != 0:
        return code
    code = run_link()
    if code != 0:
        return code
    code = run_build_graph()
    return code


def main() -> None:
    """Run the full SecondSelf pipeline.
    * By default runs classify (unprocessed captures) → link → build_graph.
    * Use ``--force`` to re‑classify all captures.
    """
    import argparse
    parser = argparse.ArgumentParser(description="Run full pipeline: classify → link → build_graph")
    parser.add_argument("--force", action="store_true", help="Force re‑classification of all captures")
    args = parser.parse_args()

    exit_code = run_full_pipeline(force_classify=args.force)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
