#!/usr/bin/env python3
"""
generate_index.py

Scans the quizzes/ directory for exported Lumi/H5P HTML files,
extracts quiz metadata (title, exercise type, etc.), and generates
a clean, minimal, responsive index.html portal with direct links
and 'Copy link' small buttons.
"""

import os
import re
import json
import html
import argparse
from pathlib import Path

# Mapping of common H5P library keys to clean human-readable names
H5P_LIBRARY_NAMES = {
    "Blanks": "Fill in the Blanks",
    "DragQuestion": "Drag and Drop",
    "MultiChoice": "Multiple Choice",
    "SingleChoiceSet": "Single Choice Set",
    "Summary": "Summary",
    "InteractiveVideo": "Interactive Video",
    "TrueFalse": "True / False",
    "Column": "Column Activity",
    "CoursePresentation": "Course Presentation",
    "MemoryGame": "Memory Game",
    "Dialogcards": "Dialog Cards",
    "FindTheWords": "Find the Words",
    "MarkTheWords": "Mark the Words",
    "DragText": "Drag Text",
    "Flashcards": "Flashcards",
    "Questionnaire": "Questionnaire",
}

DEFAULT_RESULTS_URL = (
    os.environ.get("RESULTS_URL", "").strip()
    or "https://docs.google.com/spreadsheets/d/1mO893ESTXibzcYJctNgFFBaJz8950gYkCsjPpCMIrN0/edit?pli=1&gid=0#gid=0"
)


def clean_title_from_filename(filename: str) -> str:
    """Generate a clean fallback title from the filename."""
    stem = Path(filename).stem
    # Replace dashes/underscores with spaces
    cleaned = re.sub(r"[-_]+", " ", stem).strip()
    return cleaned.capitalize()


def extract_metadata(filepath: str) -> dict:
    """Extract quiz title and library type from H5P HTML content."""
    filename = os.path.basename(filepath)
    title = None
    library_type = None

    try:
        # Read the first 512 KB where H5PIntegration configuration is placed
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            chunk = f.read(524288)

        # 1. Look for metadata title: "metadata":{"license":"...","title":"..."}
        m_meta = re.search(r'"metadata"\s*:\s*\{[^}]*?"title"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', chunk)
        if m_meta:
            try:
                title = json.loads(f'"{m_meta.group(1)}"')
            except Exception:
                title = m_meta.group(1)

        # 2. Fallback to mainTitle or title inside JSON
        if not title:
            m_main = re.search(r'"mainTitle"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', chunk)
            if m_main:
                try:
                    title = json.loads(f'"{m_main.group(1)}"')
                except Exception:
                    title = m_main.group(1)

        # 3. Fallback to HTML <title> tag
        if not title:
            m_tag = re.search(r"<title[^>]*>(.*?)</title>", chunk, re.IGNORECASE | re.DOTALL)
            if m_tag:
                title = m_tag.group(1).strip()

        # Extract library type (e.g., "H5P.Blanks 1.14")
        m_lib = re.search(r'"library"\s*:\s*"H5P\.([A-Za-z]+)[^"]*"', chunk)
        if m_lib:
            lib_raw = m_lib.group(1)
            library_type = H5P_LIBRARY_NAMES.get(lib_raw, lib_raw)

    except Exception as e:
        print(f"Warning: could not parse metadata for {filepath}: {e}")

    if not title or not title.strip():
        title = clean_title_from_filename(filename)

    return {
        "filename": filename,
        "title": title.strip(),
        "type": library_type or "Exercise",
    }


def scan_quizzes(quiz_dir: str) -> list:
    """Scan directory and return sorted list of quiz metadata dicts."""
    quizzes = []
    if not os.path.isdir(quiz_dir):
        return quizzes

    candidates = [quiz_dir]
    nested_dir = os.path.join(quiz_dir, "quizzes")
    if os.path.isdir(nested_dir):
        candidates.append(nested_dir)

    seen = set()
    for target_dir in candidates:
        for fname in sorted(os.listdir(target_dir)):
            if fname.lower().endswith(".html") and not fname.startswith("."):
                full_path = os.path.join(target_dir, fname)
                if os.path.isfile(full_path) and full_path not in seen:
                    seen.add(full_path)
                    meta = extract_metadata(full_path)
                    meta["filename"] = os.path.relpath(full_path, quiz_dir)
                    quizzes.append(meta)

    # Sort alphabetically by title
    quizzes.sort(key=lambda x: x["title"].lower())
    return quizzes


def render_html(quizzes: list, link_prefix: str = "", results_url: str = "") -> str:
    """Generate the minimal and clean index.html string."""
    effective_results_url = (results_url or "").strip() or DEFAULT_RESULTS_URL
    cards_html = []
    quizzes_json_data = []
    safe_results_url = html.escape(effective_results_url)

    for item in quizzes:
        href = f"{link_prefix}{item['filename']}"
        safe_title = html.escape(item["title"])
        safe_type = html.escape(item["type"])
        safe_filename = html.escape(item["filename"])
        safe_href = html.escape(href)

        quizzes_json_data.append({
            "title": item["title"],
            "filename": item["filename"],
            "type": item["type"],
            "href": href,
        })

        cards_html.append(f"""        <li class="quiz-item" data-title="{safe_title.lower()}" data-filename="{safe_filename.lower()}">
          <div class="quiz-info">
            <a href="{safe_href}" class="quiz-title-link">
              <span class="quiz-title">{safe_title}</span>
            </a>
            <div class="quiz-meta">
              <span class="badge badge-type">{safe_type}</span>
              <span class="badge badge-file">{safe_filename}</span>
            </div>
          </div>
          <div class="quiz-actions">
            <button type="button" class="btn btn-copy" data-href="{safe_href}" title="Copy shareable link" aria-label="Copy link to {safe_title}">
              <svg class="icon icon-copy" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <svg class="icon icon-check" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:none;">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              <span class="btn-text">Copy link</span>
            </button>
            <a href="{safe_href}" class="btn btn-open" title="Open quiz">
              <span>Open</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </a>
          </div>
        </li>""")

    cards_joined = "\n".join(cards_html)
    count = len(quizzes)
    count_label = f"{count} {'exercise' if count == 1 else 'exercises'}"

    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Interactive German Quizzes</title>
  <meta name="description" content="Portal for interactive German language quizzes and exercises.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      --bg-page: #f8fafc;
      --bg-card: #ffffff;
      --border-color: #e2e8f0;
      --border-hover: #cbd5e1;
      --text-main: #0f172a;
      --text-muted: #64748b;
      --text-subtle: #94a3b8;
      --primary: #0284c7;
      --primary-hover: #0369a1;
      --primary-light: #e0f2fe;
      --badge-bg: #f1f5f9;
      --badge-text: #475569;
      --success: #16a34a;
      --success-light: #dcfce7;
      --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
      --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 14px;
    }}

    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg-page: #090d16;
        --bg-card: #131b2e;
        --border-color: #1e293b;
        --border-hover: #334155;
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        --text-subtle: #64748b;
        --primary: #38bdf8;
        --primary-hover: #7dd3fc;
        --primary-light: rgba(56, 189, 248, 0.12);
        --badge-bg: #1e293b;
        --badge-text: #cbd5e1;
        --success: #4ade80;
        --success-light: rgba(74, 222, 128, 0.15);
        --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.4);
        --shadow-md: 0 4px 12px 0 rgba(0, 0, 0, 0.5);
      }}
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: var(--font-family);
      background-color: var(--bg-page);
      color: var(--text-main);
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
      min-height: 100vh;
      padding: 40px 20px 80px;
    }}

    .container {{
      max-width: 760px;
      margin: 0 auto;
    }}

    /* Header */
    header {{
      margin-bottom: 32px;
    }}

    .header-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }}

    .header-title-group {{
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .btn-results {{
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 6px 13px;
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--text-main);
      background-color: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      text-decoration: none;
      box-shadow: var(--shadow-sm);
      transition: all 0.15s ease;
      white-space: nowrap;
    }}

    .btn-results:hover {{
      border-color: var(--border-hover);
      background-color: var(--badge-bg);
      color: var(--primary);
      box-shadow: var(--shadow-md);
      transform: translateY(-1px);
    }}

    .btn-results .icon-sheet {{
      color: #10b981;
    }}

    .btn-results .icon-external {{
      color: var(--text-subtle);
    }}

    h1 {{
      font-size: 1.75rem;
      font-weight: 700;
      letter-spacing: -0.025em;
      color: var(--text-main);
    }}

    .count-pill {{
      display: inline-flex;
      align-items: center;
      padding: 3px 10px;
      font-size: 0.8125rem;
      font-weight: 500;
      background-color: var(--primary-light);
      color: var(--primary);
      border-radius: 9999px;
    }}

    .subtitle {{
      color: var(--text-muted);
      font-size: 0.9375rem;
    }}

    /* Search & Filter */
    .controls {{
      margin-bottom: 24px;
      position: relative;
    }}

    .search-wrapper {{
      position: relative;
      display: flex;
      align-items: center;
    }}

    .search-icon {{
      position: absolute;
      left: 14px;
      color: var(--text-subtle);
      pointer-events: none;
    }}

    .search-input {{
      width: 100%;
      padding: 10px 16px 10px 42px;
      font-size: 0.9375rem;
      font-family: inherit;
      background-color: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      color: var(--text-main);
      box-shadow: var(--shadow-sm);
      outline: none;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }}

    .search-input:focus {{
      border-color: var(--primary);
      box-shadow: 0 0 0 3px var(--primary-light);
    }}

    .search-input::placeholder {{
      color: var(--text-subtle);
    }}

    /* Quiz List */
    .quiz-list {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .quiz-item {{
      background-color: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      box-shadow: var(--shadow-sm);
      transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
    }}

    .quiz-item:hover {{
      border-color: var(--border-hover);
      box-shadow: var(--shadow-md);
      transform: translateY(-1px);
    }}

    .quiz-info {{
      flex: 1;
      min-width: 0;
    }}

    .quiz-title-link {{
      text-decoration: none;
      color: inherit;
      display: inline-block;
      max-width: 100%;
    }}

    .quiz-title {{
      font-size: 1.05rem;
      font-weight: 600;
      color: var(--text-main);
      display: block;
      word-wrap: break-word;
      transition: color 0.15s ease;
    }}

    .quiz-title-link:hover .quiz-title {{
      color: var(--primary);
    }}

    .quiz-meta {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 6px;
      flex-wrap: wrap;
    }}

    .badge {{
      display: inline-flex;
      align-items: center;
      font-size: 0.75rem;
      font-weight: 500;
      padding: 2px 8px;
      border-radius: var(--radius-sm);
      background-color: var(--badge-bg);
      color: var(--badge-text);
      line-height: 1.4;
    }}

    .badge-file {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      color: var(--text-muted);
      opacity: 0.85;
    }}

    /* Buttons */
    .quiz-actions {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }}

    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      font-size: 0.8125rem;
      font-weight: 500;
      font-family: inherit;
      border-radius: var(--radius-sm);
      text-decoration: none;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.15s ease;
      white-space: nowrap;
      user-select: none;
    }}

    /* Copy Link Button */
    .btn-copy {{
      background-color: transparent;
      color: var(--text-muted);
      border-color: var(--border-color);
    }}

    .btn-copy:hover {{
      background-color: var(--badge-bg);
      color: var(--text-main);
      border-color: var(--border-hover);
    }}

    .btn-copy.copied {{
      background-color: var(--success-light);
      color: var(--success);
      border-color: var(--success);
    }}

    /* Open Button */
    .btn-open {{
      background-color: var(--primary-light);
      color: var(--primary);
      border-color: transparent;
    }}

    .btn-open:hover {{
      background-color: var(--primary);
      color: #ffffff;
    }}

    /* Empty state */
    .empty-state {{
      display: none;
      text-align: center;
      padding: 48px 16px;
      color: var(--text-muted);
    }}

    .empty-state p {{
      font-size: 0.9375rem;
      margin-top: 8px;
    }}

    /* Toast Notification */
    .toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background-color: #0f172a;
      color: #ffffff;
      padding: 10px 18px;
      border-radius: var(--radius-md);
      font-size: 0.875rem;
      font-weight: 500;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
      display: flex;
      align-items: center;
      gap: 8px;
      opacity: 0;
      transform: translateY(12px);
      pointer-events: none;
      transition: opacity 0.2s ease, transform 0.2s ease;
      z-index: 999;
    }}

    .toast.show {{
      opacity: 1;
      transform: translateY(0);
    }}

    @media (max-width: 580px) {{
      body {{
        padding: 24px 14px 60px;
      }}

      .quiz-item {{
        flex-direction: column;
        align-items: flex-start;
        padding: 14px 16px;
      }}

      .quiz-actions {{
        width: 100%;
        justify-content: flex-end;
        padding-top: 8px;
        border-top: 1px dashed var(--border-color);
      }}

      .btn {{
        flex: 1;
        justify-content: center;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="header-top">
        <div class="header-title-group">
          <h1>Interactive German Quizzes</h1>
          <span class="count-pill" id="quiz-count">{count_label}</span>
        </div>
        <a href="{safe_results_url}" target="_blank" rel="noopener noreferrer" class="btn-results" title="Open student results in Google Sheets (new window)">
          <svg class="icon-sheet" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
          <span>Results</span>
          <svg class="icon-external" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
        </a>
      </div>
      <p class="subtitle">Practice grammar, vocabulary, and sentence structures with automated feedback.</p>
    </header>

    <div class="controls">
      <div class="search-wrapper">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
        <input type="text" id="search-input" class="search-input" placeholder="Filter quizzes by title or keyword..." autocomplete="off">
      </div>
    </div>

    <main>
      <ul class="quiz-list" id="quiz-list">
{cards_joined}
      </ul>

      <div class="empty-state" id="empty-state">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color:var(--text-subtle);">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
        <p>No matching quizzes found.</p>
      </div>
    </main>
  </div>

  <div class="toast" id="toast" role="status" aria-live="polite">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color:#4ade80;">
      <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
    <span>Link copied to clipboard!</span>
  </div>

  <script>
    (function () {{
      const searchInput = document.getElementById('search-input');
      const quizList = document.getElementById('quiz-list');
      const quizItems = Array.from(quizList.querySelectorAll('.quiz-item'));
      const emptyState = document.getElementById('empty-state');
      const quizCount = document.getElementById('quiz-count');
      const toast = document.getElementById('toast');
      let toastTimeout = null;

      // Show toast helper
      function showToast(message) {{
        if (toastTimeout) clearTimeout(toastTimeout);
        toast.querySelector('span').textContent = message;
        toast.classList.add('show');
        toastTimeout = setTimeout(() => {{
          toast.classList.remove('show');
        }}, 2200);
      }}

      // Compute full shareable URL
      function getShareableUrl(href) {{
        const cleanName = href.replace(/^quizzes\\//, '').replace(/^\\.\\//, '');
        // On file: protocol or local preview, default to canonical GitHub Pages link
        if (window.location.protocol === 'file:') {{
          return 'https://boba-and-co.github.io/de-in-be/' + cleanName;
        }}
        try {{
          // Resolve relative to current directory/origin dynamically
          return new URL(cleanName, window.location.href).href;
        }} catch (e) {{
          return window.location.origin + '/' + cleanName;
        }}
      }}

      // Copy Link Handler
      document.addEventListener('click', async function (e) {{
        const btn = e.target.closest('.btn-copy');
        if (!btn) return;

        const href = btn.getAttribute('data-href');
        const urlToCopy = getShareableUrl(href);

        let copied = false;
        try {{
          if (navigator.clipboard && navigator.clipboard.writeText) {{
            await navigator.clipboard.writeText(urlToCopy);
            copied = true;
          }}
        }} catch (err) {{
          // Fallback if clipboard API is restricted
        }}
        if (!copied) {{
          copied = fallbackCopy(urlToCopy);
        }}

        const iconCopy = btn.querySelector('.icon-copy');
        const iconCheck = btn.querySelector('.icon-check');
        const btnText = btn.querySelector('.btn-text');

        btn.classList.add('copied');
        if (iconCopy) iconCopy.style.display = 'none';
        if (iconCheck) iconCheck.style.display = 'inline-block';
        if (btnText) btnText.textContent = 'Copied!';

        showToast('Link copied: ' + urlToCopy);

        setTimeout(() => {{
          btn.classList.remove('copied');
          if (iconCopy) iconCopy.style.display = 'inline-block';
          if (iconCheck) iconCheck.style.display = 'none';
          if (btnText) btnText.textContent = 'Copy link';
        }}, 2000);
      }});

      function fallbackCopy(text) {{
        try {{
          const textarea = document.createElement('textarea');
          textarea.value = text;
          textarea.setAttribute('readonly', '');
          textarea.style.position = 'fixed';
          textarea.style.left = '-9999px';
          textarea.style.top = '0';
          document.body.appendChild(textarea);
          textarea.focus();
          textarea.select();
          textarea.setSelectionRange(0, textarea.value.length);
          const successful = document.execCommand('copy');
          document.body.removeChild(textarea);
          return successful;
        }} catch (err) {{
          return false;
        }}
      }}

      // Search & Filter
      searchInput.addEventListener('input', function () {{
        const query = this.value.trim().toLowerCase();
        let visibleCount = 0;

        quizItems.forEach(item => {{
          const title = item.getAttribute('data-title') || '';
          const filename = item.getAttribute('data-filename') || '';
          const matches = !query || title.includes(query) || filename.includes(query);

          item.style.display = matches ? '' : 'none';
          if (matches) visibleCount++;
        }});

        emptyState.style.display = visibleCount === 0 ? 'block' : 'none';
        quizCount.textContent = visibleCount + (visibleCount === 1 ? ' exercise' : ' exercises');
      }});
    }})();
  </script>
</body>
</html>
"""
    return template


def main():
    parser = argparse.ArgumentParser(description="Generate quiz index page.")
    parser.add_argument(
        "--quizzes-dir",
        default="quizzes",
        help="Path to quizzes directory (default: quizzes)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to generated index.html. If omitted, generates both root index.html and public/index.html if public/ exists.",
    )
    parser.add_argument(
        "--public-dir",
        default=None,
        help="If specified, also outputs index.html directly into this public directory with sibling links.",
    )
    parser.add_argument(
        "--results-url",
        default=DEFAULT_RESULTS_URL,
        help="URL to Google Sheet or results dashboard (opens in new window)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    quizzes_dir = project_root / args.quizzes_dir

    effective_results_url = (args.results_url or "").strip() or DEFAULT_RESULTS_URL
    print(f"Scanning quizzes in {quizzes_dir}...")
    quizzes = scan_quizzes(str(quizzes_dir))
    print(f"Found {len(quizzes)} quizzes:")
    for q in quizzes:
        print(f"  - [{q['type']}] {q['title']} ({q['filename']})")

    # If a specific output was given:
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Determine prefix: if outputting into public, files are siblings so prefix is ""
        prefix = "" if out_path.parent.name == "public" else "quizzes/"
        html_content = render_html(quizzes, link_prefix=prefix, results_url=effective_results_url)
        out_path.write_text(html_content, encoding="utf-8")
        print(f"Generated {out_path} (prefix='{prefix}')")
        return

    # If --public-dir was specified:
    if args.public_dir:
        pub_path = Path(args.public_dir)
        pub_path.mkdir(parents=True, exist_ok=True)
        html_content = render_html(quizzes, link_prefix="", results_url=effective_results_url)
        target = pub_path / "index.html"
        target.write_text(html_content, encoding="utf-8")
        print(f"Generated {target} for deployment.")

    # Default: Generate root index.html (links to quizzes/)
    root_target = project_root / "index.html"
    root_html = render_html(quizzes, link_prefix="quizzes/", results_url=effective_results_url)
    root_target.write_text(root_html, encoding="utf-8")
    print(f"Generated {root_target}")

    # Also save a quizzes.json manifest in root
    manifest_target = project_root / "quizzes.json"
    manifest_target.write_text(json.dumps(quizzes, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {manifest_target}")

    # If public directory already exists and was not explicitly targeted via --public-dir, update it too
    public_dir = project_root / "public"
    if public_dir.is_dir() and not args.public_dir:
        pub_target = public_dir / "index.html"
        pub_html = render_html(quizzes, link_prefix="", results_url=effective_results_url)
        pub_target.write_text(pub_html, encoding="utf-8")
        print(f"Updated {pub_target}")


if __name__ == "__main__":
    main()
