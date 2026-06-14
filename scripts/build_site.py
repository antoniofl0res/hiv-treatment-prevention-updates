#!/usr/bin/env python3
"""Build a static Pages site from the report files in the repo root.

For every report (identified by file base name) the builder prefers an
existing Cowork-rendered ``.html`` file and falls back to rendering the
``.md`` source when no HTML is present. A date-sorted ``index.html`` landing
page is generated automatically, so the weekly workflow stays "drop the new
file in and push".
"""
from __future__ import annotations

import html
import re
import shutil
from datetime import date
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[_-](.+)$")
# Files that are not reports and should never appear in the listing.
SKIP_STEMS = {"README", "index"}
SKIP_FILES = {"About.txt"}


def title_from_stem(stem: str) -> tuple[date | None, str]:
    """Return (date_or_None, human_title) parsed from a file base name."""
    m = DATE_RE.match(stem)
    if m:
        y, mo, d, rest = m.groups()
        try:
            dt = date(int(y), int(mo), int(d))
        except ValueError:
            dt = None
        title = rest
    else:
        dt = None
        title = stem
    title = title.replace("_", " ").replace("-", " ").strip()
    return dt, title


def render_markdown(md_path: Path, title: str) -> str:
    text = md_path.read_text(encoding="utf-8")
    # Strip a leading YAML front-matter block if present.
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2]
    body = markdown.markdown(
        text,
        extensions=["extra", "tables", "sane_lists", "toc", "nl2br"],
    )
    return PAGE_TEMPLATE.format(title=html.escape(title), body=body)


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<main class="report">
<p class="back"><a href="index.html">&larr; All reports</a></p>
{body}
</main>
</body>
</html>
"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HIV Treatment &amp; Prevention Updates</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<main>
<header class="masthead">
<h1>HIV Treatment &amp; Prevention Updates</h1>
<p class="lede">Weekly evidence digests on HIV drug therapies and long-acting
treatment &amp; prevention pipelines, compiled by Antonio Flores
(M&eacute;decins Sans Fronti&egrave;res &mdash; Doctors Without Borders).</p>
</header>
<section class="reports">
{items}
</section>
<footer>
<p>Updated automatically from the
<a href="https://github.com/antoniofl0res/hiv-treatment-prevention-updates">source repository</a>.
These digests summarise publicly available research and are not a substitute
for primary sources or clinical guidance.</p>
</footer>
</main>
</body>
</html>
"""

STYLE = """:root{--ink:#1a1a1a;--muted:#6b6b6b;--accent:#c8102e;--line:#e6e6e6;--bg:#ffffff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;line-height:1.6}
main{max-width:820px;margin:0 auto;padding:48px 24px 80px}
.masthead{border-bottom:3px solid var(--accent);padding-bottom:24px;margin-bottom:32px}
h1{font-size:2rem;font-weight:700;letter-spacing:-.01em;margin:0 0 .4em}
.lede{color:var(--muted);font-size:1.05rem;margin:0;max-width:60ch}
.reports{display:flex;flex-direction:column}
.report-row{display:flex;justify-content:space-between;align-items:baseline;
gap:16px;padding:16px 0;border-bottom:1px solid var(--line);text-decoration:none;color:inherit}
.report-row:hover .report-title{color:var(--accent)}
.report-title{font-weight:600;font-size:1.08rem}
.report-date{color:var(--muted);font-size:.9rem;white-space:nowrap}
.section-label{font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;
color:var(--muted);margin:32px 0 4px;font-weight:700}
footer{margin-top:48px;color:var(--muted);font-size:.85rem}
a{color:var(--accent)}
.report{max-width:760px}
.report .back{font-size:.9rem;margin-bottom:24px}
.report h1,.report h2,.report h3{letter-spacing:-.01em}
.report table{border-collapse:collapse;width:100%;margin:1em 0}
.report th,.report td{border:1px solid var(--line);padding:8px 10px;text-align:left}
.report th{background:#fafafa}
"""


def main() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "assets").mkdir(parents=True)
    (SITE / "assets" / "style.css").write_text(STYLE, encoding="utf-8")

    # Collect report stems from .md and .html files in the repo root.
    stems: dict[str, dict[str, Path]] = {}
    for p in ROOT.glob("*.md"):
        if p.stem in SKIP_STEMS:
            continue
        stems.setdefault(p.stem, {})["md"] = p
    for p in ROOT.glob("*.html"):
        if p.stem in SKIP_STEMS:
            continue
        stems.setdefault(p.stem, {})["html"] = p

    entries = []
    for stem, sources in stems.items():
        dt, title = title_from_stem(stem)
        out_name = f"{stem}.html"
        if "html" in sources:
            shutil.copyfile(sources["html"], SITE / out_name)
        else:
            (SITE / out_name).write_text(
                render_markdown(sources["md"], title), encoding="utf-8"
            )
        entries.append((dt, title, out_name))

    # Sort: dated reports newest-first, then undated reports alphabetically.
    dated = sorted([e for e in entries if e[0]], key=lambda e: e[0], reverse=True)
    undated = sorted([e for e in entries if not e[0]], key=lambda e: e[1])

    rows = []
    for dt, title, name in dated:
        rows.append(
            f'<a class="report-row" href="{html.escape(name)}">'
            f'<span class="report-title">{html.escape(title)}</span>'
            f'<span class="report-date">{dt.strftime("%b %d, %Y")}</span></a>'
        )
    if undated:
        rows.append('<div class="section-label">Special reports</div>')
        for _dt, title, name in undated:
            rows.append(
                f'<a class="report-row" href="{html.escape(name)}">'
                f'<span class="report-title">{html.escape(title)}</span></a>'
            )

    (SITE / "index.html").write_text(
        INDEX_TEMPLATE.format(items="\n".join(rows)), encoding="utf-8"
    )
    print(f"Built {len(entries)} report pages into {SITE}")


if __name__ == "__main__":
    main()
