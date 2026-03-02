#!/usr/bin/env python3
"""
Internal Linker for DiggingScriptures Research Articles
========================================================
Analyzes and remediates internal linking across 680 research articles.
Three-phase architecture:
  Phase 1: Inventory & Graph Build
  Phase 2: Topic Matching (weighted scoring)
  Phase 3: Link Injection (hub links + Related Research section)

Usage:
  python internal_linker.py --audit              # Report orphans & under-linked
  python internal_linker.py --fix                 # Inject links
  python internal_linker.py --fix --min-links 5   # Custom minimum
  python internal_linker.py --fix --category biblical-archaeology

Can also be imported by SemanticPipe for --fix-links integration.
"""

import os, sys, re, argparse, json
from pathlib import Path
from collections import defaultdict, Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESEARCH_DIR = os.path.join(BASE_DIR, "src", "content", "research")

CATEGORIES = ["biblical-archaeology", "scripture", "excavations", "artifacts", "faith"]

HUB_URLS = {
    "biblical-archaeology": "/research/biblical-archaeology",
    "scripture": "/research/scripture",
    "excavations": "/research/excavations",
    "artifacts": "/research/artifacts",
    "faith": "/research/faith",
}

MIN_LINKS = 3   # articles below this get remediated
MAX_LINKS = 10  # don't inject beyond this total
TARGET_RELATED = 4  # how many Related Research links to add

# Common English stop words (for keyword extraction)
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "was", "are", "be",
    "this", "that", "these", "those", "will", "would", "could", "should",
    "has", "have", "had", "been", "being", "do", "does", "did", "not",
    "so", "if", "about", "into", "through", "during", "before", "after",
    "above", "below", "between", "under", "over", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how",
    "all", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "only", "own", "same", "than", "too", "very",
    "can", "just", "don", "now", "its", "also", "what", "which", "who",
    "whom", "their", "them", "we", "our", "you", "your", "up", "out",
    "off", "down", "new", "old", "one", "two", "may", "get", "got",
    "many", "much", "while", "yet", "still", "even", "upon", "per",
}


# ═══════════════════════════════════════════════════════════════
# Phase 1: Inventory & Graph Build
# ═══════════════════════════════════════════════════════════════

def extract_title(raw):
    """Pull title from YAML frontmatter."""
    m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', raw, re.MULTILINE)
    return m.group(1).strip() if m else ""

def extract_category(raw):
    """Pull category from YAML frontmatter."""
    m = re.search(r'^category:\s*["\']?(.+?)["\']?\s*$', raw, re.MULTILINE)
    return m.group(1).strip() if m else ""

def extract_body(raw):
    """Get the body text after frontmatter."""
    if raw.startswith("---"):
        idx = raw.index("---", 3)
        return raw[idx+3:].lstrip("\n")
    return raw

def extract_internal_links(body):
    """Find all internal links in markdown body. Returns set of URL paths."""
    links = set()
    # Markdown links: [text](/path) or [text](/path "title")
    for m in re.finditer(r'\[([^\]]+)\]\((/[^)"\s]+)', body):
        links.add(m.group(2))
    # HTML links: href="/path"
    for m in re.finditer(r'href=["\'](/[^"\']+)["\']', body):
        links.add(m.group(1))
    return links

def extract_keywords(text, min_len=4):
    """Extract meaningful keywords from text, stop-word filtered."""
    words = re.findall(r'[a-z]{%d,}' % min_len, text.lower())
    return {w for w in words if w not in STOP_WORDS}

def build_inventory():
    """
    Scan all research articles. Returns dict keyed by slug:
    {slug: {filepath, title, category, url, body, title_keywords, body_keywords, outbound_links, inbound_count}}
    """
    inventory = {}
    for cat in CATEGORIES:
        cat_dir = os.path.join(RESEARCH_DIR, cat)
        if not os.path.isdir(cat_dir):
            continue
        for fname in sorted(os.listdir(cat_dir)):
            if not fname.endswith(".md"):
                continue
            slug = fname[:-3]
            filepath = os.path.join(cat_dir, fname)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw = f.read()
            except Exception:
                continue

            title = extract_title(raw)
            category = extract_category(raw) or cat
            body = extract_body(raw)
            url = f"/research/{category}/{slug}"

            # Keywords from title (high value) and body (lower value)
            title_kw = extract_keywords(title)
            # For body keywords, sample first 2000 chars for speed
            body_kw = extract_keywords(body[:2000])

            outbound = extract_internal_links(body)

            inventory[slug] = {
                "filepath": filepath,
                "title": title,
                "category": category,
                "url": url,
                "body": body,
                "title_keywords": title_kw,
                "body_keywords": body_kw,
                "outbound_links": outbound,
                "inbound_count": 0,  # filled in next pass
            }

    # Second pass: count inbound links
    # Build a URL-to-slug lookup
    url_to_slug = {info["url"]: slug for slug, info in inventory.items()}
    # Also handle partial matches (some links might omit /research/ prefix or have trailing /)
    for slug, info in inventory.items():
        for link_url in info["outbound_links"]:
            # Normalize: strip trailing slash
            norm = link_url.rstrip("/")
            target_slug = url_to_slug.get(norm)
            if not target_slug:
                # Try matching just the last segment
                last_seg = norm.split("/")[-1]
                if last_seg in inventory:
                    target_slug = last_seg
            if target_slug and target_slug != slug:
                inventory[target_slug]["inbound_count"] += 1

    return inventory


# ═══════════════════════════════════════════════════════════════
# Phase 2: Topic Matching
# ═══════════════════════════════════════════════════════════════

def compute_match_score(source, target):
    """
    Weighted relevance score between two articles.
    Higher = better match for internal linking.
    """
    score = 0.0

    # 1. Shared title keywords (strongest signal — titles are dense with topic)
    shared_title = source["title_keywords"] & target["title_keywords"]
    score += len(shared_title) * 3

    # 2. Same category bonus (respects hub-spoke topical silos)
    if source["category"] == target["category"]:
        score += 2

    # 3. Shared body keywords (weaker but useful for topical adjacency)
    shared_body = source["body_keywords"] & target["body_keywords"]
    score += min(len(shared_body), 8) * 1  # cap at 8 to avoid long-article bias

    # 4. Penalty if already linked (don't duplicate)
    if target["url"] in source["outbound_links"]:
        score -= 10  # heavy penalty — effectively removes from candidates

    return score

def find_best_targets(slug, inventory, count=TARGET_RELATED):
    """
    Find the top N most relevant articles to link to from `slug`.
    Returns list of (target_slug, score) tuples, highest first.
    """
    source = inventory[slug]
    candidates = []

    for target_slug, target in inventory.items():
        if target_slug == slug:
            continue
        score = compute_match_score(source, target)
        if score > 0:
            candidates.append((target_slug, score))

    # Sort by score descending, break ties by inbound_count (prefer under-linked targets)
    candidates.sort(key=lambda x: (-x[1], inventory[x[0]]["inbound_count"]))
    return candidates[:count]


# ═══════════════════════════════════════════════════════════════
# Phase 3: Link Injection
# ═══════════════════════════════════════════════════════════════

def inject_hub_link(body, category, title):
    """
    If article doesn't link to its category hub, add a contextual
    hub link sentence to the first paragraph.
    Returns (new_body, was_changed).
    """
    hub_url = HUB_URLS.get(category)
    if not hub_url:
        return body, False

    existing = extract_internal_links(body)
    # Check if any existing link points to the hub
    if any(link.rstrip("/") == hub_url for link in existing):
        return body, False

    # Build hub link sentence based on category
    hub_names = {
        "biblical-archaeology": "biblical archaeology",
        "scripture": "biblical scripture studies",
        "excavations": "archaeological excavations",
        "artifacts": "ancient artifacts",
        "faith": "faith and history",
    }
    hub_label = hub_names.get(category, category.replace("-", " "))
    hub_sentence = f"This topic is part of our [research on {hub_label}]({hub_url})."

    # Find first real paragraph and append hub sentence after it
    lines = body.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip blank lines, headings, images, HTML
        if not stripped or stripped.startswith("#") or stripped.startswith("!") or stripped.startswith("<"):
            continue
        # Found first content line — append hub sentence after this paragraph
        # Find end of this paragraph (next blank line or heading)
        j = i + 1
        while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith("#"):
            j += 1
        # Insert hub sentence after the paragraph
        lines.insert(j, "\n" + hub_sentence + "\n")
        body = "\n".join(lines)
        return body, True

    return body, False


def inject_related_section(body, targets, inventory):
    """
    Append a '## Related Research' section with contextual links.
    Places it before the FAQ section if one exists, otherwise at the end.
    Returns (new_body, links_added_count).
    """
    if not targets:
        return body, 0

    # Build the Related Research markdown
    lines_md = ["\n## Related Research\n"]
    lines_md.append("Explore these related articles for deeper study:\n")
    for target_slug, _score in targets:
        t = inventory[target_slug]
        title = t["title"]
        url = t["url"]
        lines_md.append(f"- [{title}]({url})")
    lines_md.append("")  # trailing newline
    related_block = "\n".join(lines_md)

    # Check if there's already a Related Research section — skip if so
    if re.search(r"^##\s+Related\s+Research", body, re.MULTILINE | re.I):
        return body, 0

    # Place before FAQ section if it exists
    faq_match = re.search(r"^##\s+.*(?:FAQ|Frequently Asked|Common Questions)", body, re.MULTILINE | re.I)
    if faq_match:
        insert_pos = faq_match.start()
        body = body[:insert_pos].rstrip() + "\n" + related_block + "\n" + body[insert_pos:]
    else:
        body = body.rstrip() + "\n" + related_block + "\n"

    return body, len(targets)


def fix_article_links(slug, inventory, min_links=MIN_LINKS, max_links=MAX_LINKS):
    """
    Fix internal linking for a single article.
    Returns (new_body, changes_list) or (None, []) if no changes needed.
    """
    info = inventory[slug]
    body = info["body"]
    current_count = len(info["outbound_links"])
    changes = []

    # Skip articles that already meet the threshold
    if current_count >= min_links:
        return None, []

    # How many links do we need to add?
    needed = min(min_links - current_count, max_links - current_count, TARGET_RELATED + 1)
    if needed <= 0:
        return None, []

    # 1. Hub link injection
    new_body, hub_added = inject_hub_link(body, info["category"], info["title"])
    if hub_added:
        changes.append(f"Injected hub link to {HUB_URLS[info['category']]}")
        needed -= 1

    # 2. Related Research section
    if needed > 0:
        targets = find_best_targets(slug, inventory, count=min(needed, TARGET_RELATED))
        new_body, related_count = inject_related_section(new_body, targets, inventory)
        if related_count > 0:
            changes.append(f"Added Related Research section ({related_count} links)")

    if not changes:
        return None, []

    return new_body, changes


def save_body(filepath, new_body):
    """Save updated body while preserving frontmatter."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()
    if not raw.startswith("---"):
        return False
    idx = raw.index("---", 3)
    header = raw[:idx + 3]
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header + new_body)
    return True


# ═══════════════════════════════════════════════════════════════
# Public API (for SemanticPipe integration)
# ═══════════════════════════════════════════════════════════════

_cached_inventory = None

def get_inventory(force_rebuild=False):
    """Lazy-load and cache the inventory for reuse within a pipeline run."""
    global _cached_inventory
    if _cached_inventory is None or force_rebuild:
        _cached_inventory = build_inventory()
    return _cached_inventory

def fix_links_for_body(slug, body, category, inventory=None):
    """
    SemanticPipe integration point. Takes a slug, current body, and category.
    Returns (new_body, changes_list). Does NOT save — SemanticPipe handles saving.
    """
    if inventory is None:
        inventory = get_inventory()

    # Update the inventory entry with the current body (may have been modified by earlier pipeline steps)
    if slug in inventory:
        info = inventory[slug]
        info["body"] = body
        info["outbound_links"] = extract_internal_links(body)
        info["title_keywords"] = extract_keywords(info["title"])
        info["body_keywords"] = extract_keywords(body[:2000])
    else:
        return body, []

    current_count = len(info["outbound_links"])
    if current_count >= MIN_LINKS:
        return body, []

    changes = []
    new_body = body

    # Hub link
    new_body, hub_added = inject_hub_link(new_body, category, info["title"])
    if hub_added:
        changes.append(f"Injected hub link to {HUB_URLS.get(category, '')}")

    # Related Research
    needed = max(MIN_LINKS - current_count - (1 if hub_added else 0), 0)
    if needed > 0:
        targets = find_best_targets(slug, inventory, count=min(needed + 1, TARGET_RELATED))
        new_body, rc = inject_related_section(new_body, targets, inventory)
        if rc > 0:
            changes.append(f"Added Related Research ({rc} links)")

    return new_body, changes


# ═══════════════════════════════════════════════════════════════
# Audit Report
# ═══════════════════════════════════════════════════════════════

def run_audit(inventory, category_filter=None):
    """Print a detailed audit report of internal linking health."""
    articles = inventory
    if category_filter:
        articles = {s: i for s, i in articles.items() if i["category"] == category_filter}

    total = len(articles)
    orphans = {s: i for s, i in articles.items() if i["inbound_count"] == 0}
    under_linked = {s: i for s, i in articles.items()
                    if len(i["outbound_links"]) < MIN_LINKS}
    zero_outbound = {s: i for s, i in articles.items()
                     if len(i["outbound_links"]) == 0}

    print(f"\n{'='*70}")
    print(f"  INTERNAL LINK AUDIT — DiggingScriptures Research")
    print(f"{'='*70}")
    print(f"  Total articles:        {total}")
    print(f"  Orphans (0 inbound):   {len(orphans)}  {'** CRITICAL **' if orphans else 'OK'}")
    print(f"  Zero outbound links:   {len(zero_outbound)}")
    print(f"  Under-linked (<{MIN_LINKS}):  {len(under_linked)}")
    print()

    # Per-category breakdown
    print(f"  BY CATEGORY:")
    for cat in CATEGORIES:
        cat_arts = {s: i for s, i in articles.items() if i["category"] == cat}
        if not cat_arts:
            continue
        cat_orphans = sum(1 for i in cat_arts.values() if i["inbound_count"] == 0)
        cat_under = sum(1 for i in cat_arts.values() if len(i["outbound_links"]) < MIN_LINKS)
        avg_out = sum(len(i["outbound_links"]) for i in cat_arts.values()) / len(cat_arts)
        avg_in = sum(i["inbound_count"] for i in cat_arts.values()) / len(cat_arts)
        print(f"    {cat:25s}  {len(cat_arts):3d} articles  "
              f"avg_out={avg_out:.1f}  avg_in={avg_in:.1f}  "
              f"orphans={cat_orphans}  under={cat_under}")

    # Top orphans
    if orphans:
        print(f"\n  ORPHAN PAGES (0 inbound — search engines may miss these):")
        for slug in sorted(orphans.keys())[:20]:
            info = orphans[slug]
            out_count = len(info["outbound_links"])
            print(f"    [{info['category'][:12]:12s}] out={out_count}  {slug[:55]}")
        if len(orphans) > 20:
            print(f"    ... and {len(orphans) - 20} more")

    # Bottom 10 by outbound count
    bottom = sorted(articles.items(), key=lambda x: len(x[1]["outbound_links"]))[:10]
    print(f"\n  BOTTOM 10 (fewest outbound links):")
    for slug, info in bottom:
        out_count = len(info["outbound_links"])
        in_count = info["inbound_count"]
        print(f"    [{info['category'][:12]:12s}] out={out_count} in={in_count}  {slug[:55]}")

    print(f"\n{'='*70}")
    return {
        "total": total,
        "orphans": len(orphans),
        "zero_outbound": len(zero_outbound),
        "under_linked": len(under_linked),
    }


# ═══════════════════════════════════════════════════════════════
# CLI: Fix Mode
# ═══════════════════════════════════════════════════════════════

def run_fix(inventory, min_links=MIN_LINKS, max_links=MAX_LINKS, category_filter=None, dry_run=False):
    """Fix under-linked articles by injecting hub links and Related Research sections."""
    articles = inventory
    if category_filter:
        articles = {s: i for s, i in articles.items() if i["category"] == category_filter}

    fixed = 0
    hub_links_added = 0
    related_links_added = 0
    skipped = 0

    for slug, info in sorted(articles.items()):
        current_count = len(info["outbound_links"])
        if current_count >= min_links:
            skipped += 1
            continue

        new_body, changes = fix_article_links(slug, inventory, min_links, max_links)
        if new_body is None:
            skipped += 1
            continue

        for c in changes:
            if "hub link" in c.lower():
                hub_links_added += 1
            if "Related Research" in c:
                # Count individual links from the change message
                m = re.search(r'\((\d+) links?\)', c)
                if m:
                    related_links_added += int(m.group(1))

        if not dry_run:
            save_body(info["filepath"], new_body)

        fixed += 1
        if fixed <= 10 or fixed % 50 == 0:
            print(f"  [{fixed:3d}] {slug[:50]:50s}  +{len(changes)} changes")

    print(f"\n{'='*70}")
    print(f"  INTERNAL LINKER RESULTS")
    print(f"{'='*70}")
    print(f"  Articles processed:    {len(articles)}")
    print(f"  Already adequate:      {skipped}")
    print(f"  Fixed:                 {fixed}")
    print(f"  Hub links injected:    {hub_links_added}")
    print(f"  Related links added:   {related_links_added}")
    print(f"  Mode:                  {'DRY RUN' if dry_run else 'SAVED'}")
    print(f"{'='*70}")

    return {"fixed": fixed, "hub_links": hub_links_added, "related_links": related_links_added}


# ═══════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Internal Linker for DiggingScriptures Research")
    parser.add_argument("--audit", action="store_true", help="Report orphans and under-linked pages")
    parser.add_argument("--fix", action="store_true", help="Inject links into under-linked articles")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--min-links", type=int, default=MIN_LINKS, help=f"Minimum links threshold (default: {MIN_LINKS})")
    parser.add_argument("--max-links", type=int, default=MAX_LINKS, help=f"Maximum links cap (default: {MAX_LINKS})")
    parser.add_argument("--category", type=str, default=None, help="Filter to single category")
    args = parser.parse_args()

    if not args.audit and not args.fix:
        print("Use --audit to report or --fix to remediate. Add --dry-run to preview.")
        sys.exit(0)

    print("Building article inventory and link graph...")
    inventory = build_inventory()
    print(f"  {len(inventory)} articles indexed across {len(CATEGORIES)} categories")

    if args.audit:
        run_audit(inventory, category_filter=args.category)

    if args.fix:
        run_fix(inventory, min_links=args.min_links, max_links=args.max_links,
                category_filter=args.category, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
