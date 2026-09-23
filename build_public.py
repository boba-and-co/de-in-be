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
        background: #ffffff !important;
      }
      body {
        margin: 0 !important;
        padding: 16px 16px 32px 16px !important;
        box-sizing: border-box !important;
      }
      .quiz-top-nav {
        width: 100% !important;
        max-width: 980px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        margin-top: 0 !important;
        margin-bottom: 16px !important;
        display: flex !important;
        align-items: center !important;
      }
      .quiz-back-btn {
        display: inline-flex !important;
        align-items: center !important;
        gap: 8px !important;
        padding: 8px 14px !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        color: #475569 !important;
        background-color: #f1f5f9 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        text-decoration: none !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.15s ease-in-out !important;
      }
      .quiz-back-btn:hover {
        background-color: #e2e8f0 !important;
        color: #0f172a !important;
        border-color: #cbd5e1 !important;
        text-decoration: none !important;
        transform: translateX(-2px) !important;
      }
      .quiz-back-btn svg {
        flex-shrink: 0 !important;
        transition: transform 0.15s ease-in-out !important;
      }
      .quiz-back-btn:hover svg {
        transform: translateX(-3px) !important;
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


def get_quiz_top_nav() -> str:
    return """<nav class="quiz-top-nav">
  <a href="index.html" class="quiz-back-btn" id="quiz-back-btn" title="Back to All Quizzes">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M19 12H5M12 19l-7-7 7-7"/>
    </svg>
    <span>All Quizzes</span>
  </a>
</nav>"""


def inject_tracker(html_text: str) -> str:
    text = normalize_h5p_paths(html_text)

    # Inject top navigation bar right after the REAL document <body>
    nav_html = get_quiz_top_nav()
    body_pos = text.rfind("<body")
    if body_pos != -1:
        end_body = text.find(">", body_pos)
        if end_body != -1:
            text = text[:end_body + 1] + f"\n{nav_html}\n" + text[end_body + 1:]

    # Inject dynamic back button path resolver and tracker script before </body>
    css = get_quiz_page_styles()
    nav_script = """<script>
(function() {
  var b = document.getElementById('quiz-back-btn');
  if (b) {
    var isSub = window.location.pathname.indexOf('/quizzes/') !== -1;
    b.href = isSub ? '../index.html' : './';
  }
})();
</script>"""
    script_block = format_tracker_script()
    injection = f"{css}\n{nav_script}\n{script_block}\n"

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

