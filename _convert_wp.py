#!/usr/bin/env python3
"""Convert WordPress HTML posts to Astro Markdown files for the /research/ collection."""

import json
import re
import os
import html
from datetime import datetime
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
KEEPERS_FULL = "_keepers_full.json"
FINAL_KEEPERS = "_final_keepers.json"
OUTPUT_DIR = Path("src/content/research")

# Silo → Astro category mapping
SILO_TO_CATEGORY = {
    "history": "biblical-archaeology",
    "sites": "excavations",
    "scripture": "scripture",
    "faith": "faith",
    "artifacts": "artifacts",
    "methods": "biblical-archaeology",  # fold into main
}

# Silo → parent hub mapping
SILO_TO_HUB = {
    "history": "biblical-archaeology",
    "sites": "excavations",
    "scripture": "scripture",
    "faith": "faith",
    "artifacts": "artifacts",
    "methods": "biblical-archaeology",
}

# ── HTML Cleanup ────────────────────────────────────────────────────────────

def strip_html_junk(html_str):
    """Remove affiliate links, iframes, external images, shop buttons."""
    # Remove iframes (YouTube embeds, etc.)
    html_str = re.sub(r'<iframe[^>]*>.*?</iframe>', '', html_str, flags=re.DOTALL)
    # Remove affiliate link blocks (shop-now buttons wrapped in <a><img></a>)
    html_str = re.sub(r'<a[^>]*christianbook\.com[^>]*>.*?</a>', '', html_str, flags=re.DOTALL)
    html_str = re.sub(r'<a[^>]*>[^<]*<img[^>]*shop-now[^>]*>.*?</a>', '', html_str, flags=re.DOTALL)
    html_str = re.sub(r'<a[^>]*>[^<]*<img[^>]*aiwisemind[^>]*>.*?</a>', '', html_str, flags=re.DOTALL)
    # Remove standalone external images (aiwisemind CDN, etc.)
    html_str = re.sub(r'<img[^>]*aiwisemind[^>]*/?>', '', html_str)
    html_str = re.sub(r'<img[^>]*digitaloceanspaces[^>]*/?>', '', html_str)
    # Remove empty paragraphs and whitespace-only tags
    html_str = re.sub(r'<p>\s*</p>', '', html_str)
    html_str = re.sub(r'<p>\s*<br\s*/?>\s*</p>', '', html_str)
    # Remove internal links to old diggingscriptures.com (will rebuild)
    html_str = re.sub(r'<a[^>]*diggingscriptures\.com[^>]*>(.*?)</a>', r'\1', html_str, flags=re.DOTALL)
    return html_str.strip()

# ── HTML → Markdown ─────────────────────────────────────────────────────────

def html_to_markdown(html_str):
    """Convert cleaned HTML to Markdown."""
    text = html_str

    # Headers
    for level in range(6, 0, -1):
        prefix = '#' * level
        text = re.sub(
            rf'<h{level}[^>]*>(.*?)</h{level}>',
            lambda m: f'\n{"#" * level} {m.group(1).strip()}\n',
            text, flags=re.DOTALL
        )

    # Bold and italic
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)

    # Links (keep external ones)
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)

    # Lists
    text = re.sub(r'<ul[^>]*>', '\n', text)
    text = re.sub(r'</ul>', '\n', text)
    text = re.sub(r'<ol[^>]*>', '\n', text)
    text = re.sub(r'</ol>', '\n', text)
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL)

    # Blockquotes
    text = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>',
                  lambda m: '\n> ' + m.group(1).strip().replace('\n', '\n> ') + '\n',
                  text, flags=re.DOTALL)

    # Paragraphs
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', text, flags=re.DOTALL)

    # Line breaks
    text = re.sub(r'<br\s*/?>', '\n', text)

    # Strip remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Decode HTML entities
    text = html.unescape(text)

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text

# ── Description Generator ───────────────────────────────────────────────────

def generate_description(title, text, max_len=155):
    """Generate a meta description from first meaningful paragraph."""
    # Get first 2 sentences from body
    sentences = re.split(r'(?<=[.!?])\s+', text[:500])
    desc = ""
    for s in sentences[:2]:
        s = s.strip()
        if len(s) < 20:
            continue
        if len(desc) + len(s) + 1 <= max_len:
            desc = (desc + " " + s).strip() if desc else s
        else:
            break
    if not desc:
        desc = text[:max_len].rsplit(' ', 1)[0] + "..."
    # Ensure no quotes that would break YAML
    desc = desc.replace('"', "'").replace('\n', ' ').strip()
    if len(desc) > 160:
        desc = desc[:157].rsplit(' ', 1)[0] + "..."
    return desc

# ── Main Conversion ─────────────────────────────────────────────────────────

def main():
    # Load data
    with open(KEEPERS_FULL, "r", encoding="utf-8") as f:
        all_posts = json.load(f)

    with open(FINAL_KEEPERS, "r", encoding="utf-8") as f:
        keeper_slugs = set(json.load(f))

    print(f"Loaded {len(all_posts)} full posts, {len(keeper_slugs)} keeper slugs")

    # Create output directories
    for cat in SILO_TO_CATEGORY.values():
        (OUTPUT_DIR / cat).mkdir(parents=True, exist_ok=True)

    converted = 0
    skipped = 0
    errors = []

    for post in all_posts:
        slug = post["slug"]
        if slug not in keeper_slugs:
            skipped += 1
            continue

        try:
            # Clean and convert HTML
            clean_html = strip_html_junk(post.get("content_html", ""))
            markdown_body = html_to_markdown(clean_html)

            if len(markdown_body.strip()) < 100:
                errors.append(f"EMPTY: {slug}")
                continue

            # Map silo to category
            silo = post.get("silo", "history")
            category = SILO_TO_CATEGORY.get(silo, "biblical-archaeology")
            parent_hub = SILO_TO_HUB.get(silo, "biblical-archaeology")

            # Generate description
            description = generate_description(post["title"], markdown_body)

            # Parse pub date
            pub_date_str = post.get("pub_date", "")
            try:
                pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
                pub_date_iso = pub_date.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pub_date_iso = "2024-01-01"

            # Clean title for YAML
            title = post["title"].replace('"', "'").replace("\\", "").strip()
            # Fix smart quotes / special chars
            title = title.replace("\u2018", "'").replace("\u2019", "'")
            title = title.replace("\u201c", "'").replace("\u201d", "'")

            # Build frontmatter
            frontmatter = f'''---
title: "{title}"
description: "{description}"
category: "{category}"
parentHub: "{parent_hub}"
pubDate: {pub_date_iso}
lastUpdated: {pub_date_iso}
draft: false
---'''

            # Write file
            out_path = OUTPUT_DIR / category / f"{slug}.md"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(frontmatter + "\n\n" + markdown_body + "\n")

            converted += 1

        except Exception as e:
            errors.append(f"ERROR: {slug} — {e}")

    print(f"\nConverted: {converted}")
    print(f"Skipped (not in keepers): {skipped}")
    print(f"Errors: {len(errors)}")
    for err in errors[:20]:
        print(f"  {err}")

    # Summary by category
    print("\nFiles per category:")
    for cat in set(SILO_TO_CATEGORY.values()):
        cat_dir = OUTPUT_DIR / cat
        if cat_dir.exists():
            count = len(list(cat_dir.glob("*.md")))
            print(f"  {cat}: {count}")

if __name__ == "__main__":
    main()
