#!/usr/bin/env python3
"""Copy quiz HTML files into a deployable public folder and inject tracker.js."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUIZZES_DIR = ROOT / "quizzes"
PUBLIC_DIR = ROOT / "public"
PUBLIC_QUIZZES_DIR = PUBLIC_DIR / "quizzes"
TRACKER_PATH = ROOT / "tracker.js"


def format_tracker_script() -> str:
    tracker_text = TRACKER_PATH.read_text(encoding="utf-8")
    webhook_url = (
        os.environ.get("WEBHOOK_URL", "").strip()
        or "https://script.google.com/macros/s/AKfycbwCyFNl3J7AFyLbMwLhzKyoXNodUuFoPRbuH4iGXVrHtkFLQCBepANj-i0k89p65LE4Ag/exec"
    )
    tracker_text = re.sub(
        r"const\s+WEBHOOK_URL\s*=\s*['\"][^'\"]*['\"];",
        f"const WEBHOOK_URL = '{webhook_url}';",
        tracker_text
    )
    return f"<script>\n{tracker_text}\n</script>\n"


def normalize_h5p_paths(text: str) -> str:
    return text.replace('"ajaxPath":"/h5p/ajax?action="', '"ajaxPath":"./h5p/ajax?action="')


def get_quiz_page_styles() -> str:
    return """
    <style>
      html, body {
        margin: 0 !important;
        padding: 0 !important;
        background: #f8fafc !important;
      }
      body {
        margin: 0 !important;
        padding: 24px 16px !important;
        box-sizing: border-box !important;
      }
      .h5p-content,
      .h5p-iframe,
      .h5p-container {
        width: 100% !important;
        max-width: 980px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        box-sizing: border-box !important;
      }
    </style>
    """


def inject_tracker(html_text: str) -> str:
    text = normalize_h5p_paths(html_text)
    css = get_quiz_page_styles()
    script_block = format_tracker_script()
    injection = f"{css}\n{script_block}\n"

    # Use rfind to inject before the REAL closing </body> at the end of document,
    # never before any '</body>' string literals inside embedded H5P JavaScript.
    pos = text.rfind("</body>")
    if pos != -1:
        return text[:pos] + injection + text[pos:]
    return text + injection


def main() -> None:
    if PUBLIC_DIR.exists():
        shutil.rmtree(PUBLIC_DIR)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_QUIZZES_DIR.mkdir(parents=True, exist_ok=True)

    if not QUIZZES_DIR.exists():
        raise FileNotFoundError(f"Missing quizzes directory: {QUIZZES_DIR}")

    quiz_files = sorted(QUIZZES_DIR.glob("*.html"))
    for quiz_file in quiz_files:
        raw_text = quiz_file.read_text(encoding="utf-8", errors="ignore")
        injected = inject_tracker(raw_text)
        # Write to public root (for direct exercise links https://.../<quiz>.html)
        (PUBLIC_DIR / quiz_file.name).write_text(injected, encoding="utf-8")
        # Write to public/quizzes/ (for backwards-compatible https://.../quizzes/<quiz>.html)
        (PUBLIC_QUIZZES_DIR / quiz_file.name).write_text(injected, encoding="utf-8")

    (PUBLIC_DIR / ".nojekyll").write_text("", encoding="utf-8")

    cmd = ["python3", str(ROOT / "generate_index.py"), "--public-dir", str(PUBLIC_DIR)]
    results_url = (
        os.environ.get("RESULTS_URL", "").strip()
        or "https://docs.google.com/spreadsheets/d/1mO893ESTXibzcYJctNgFFBaJz8950gYkCsjPpCMIrN0/edit?pli=1&gid=0#gid=0"
    )
    cmd.extend(["--results-url", results_url])
    subprocess.run(cmd, check=True)

    manifest_path = ROOT / "quizzes.json"
    if manifest_path.exists():
        shutil.copy2(manifest_path, PUBLIC_DIR / "quizzes.json")

    print(f"Built {PUBLIC_DIR} with {len(quiz_files)} quiz pages (accessible at both / and /quizzes/).")


if __name__ == "__main__":
    main()

