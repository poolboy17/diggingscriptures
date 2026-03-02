---
name: internal-linker
description: >
  Automated internal link analysis and injection for static Markdown content sites.
  Use when the user wants to fix orphan pages, improve internal linking, increase
  link equity distribution, find under-linked content, inject contextual links,
  or enforce minimum internal link counts across articles. Works on Markdown source
  files (not built HTML). Supports hub-spoke architectures with category-aware
  topic matching. Use this skill whenever the user mentions internal links,
  link building, orphan pages, link equity, link juice, or site structure optimization.
---

# Internal Linker Skill

## Purpose

Analyze and remediate internal linking across a static site's Markdown content.
Unlike analysis-only tools that report problems, this skill **fixes them** by
injecting contextual, topically-relevant internal links directly into article bodies.

## When to Use

- "Fix my internal linking" or "add more internal links"
- "Find orphan pages" or "which articles have no links?"
- "Improve link equity distribution"
- "Every article should have at least N internal links"
- After bulk content migration (WordPress → Astro, etc.)
- After running a sanity check that reveals linking gaps

## Architecture

The linker has three phases that run in sequence:

### Phase 1: Inventory & Graph Build
Scans all Markdown files in the content directory. For each article, extracts:
- Existing internal links (regex: `[text](/path)` and `href="/path"`)
- Title, category, slug → builds the URL each article lives at
- Title keywords (stop-word filtered) for topic matching

Outputs: a link graph (source → targets) and per-article link counts.

### Phase 2: Topic Matching
For each under-linked article, finds the best link targets using a scoring algorithm:

```
match_score = (
    3 × shared_title_keywords     # strongest signal
  + 2 × same_category_bonus       # hub-spoke architecture respect
  + 1 × shared_body_keywords      # weaker but useful signal
  - 2 × already_linked_penalty    # don't duplicate existing links
)
```

Category hub pages always get a link (e.g., `/research/biblical-archaeology`).
Cross-category links are allowed but scored lower to preserve topical silos.

### Phase 3: Link Injection
Two injection strategies, applied in order:

1. **Hub link** — If the article doesn't link to its category hub, prepend
   a contextual sentence with a hub link to the first paragraph.

2. **Related Research section** — Append a "## Related Research" section
   before the FAQ section (if present) with 3-5 topically relevant links.
   Each link includes a one-line contextual description derived from the
   target article's title.

The injector respects a configurable minimum (default: 3 internal links)
and maximum (default: 10) to avoid over-linking.

## Usage

```bash
# Audit only — report orphans and under-linked pages
python scripts/internal_linker.py --audit

# Fix links — inject links into under-linked articles
python scripts/internal_linker.py --fix

# Fix with custom minimum
python scripts/internal_linker.py --fix --min-links 5

# Target a single category
python scripts/internal_linker.py --fix --category biblical-archaeology
```

## Configuration

Edit the constants at the top of `internal_linker.py`:
- `CONTENT_DIR` — path to Markdown content directory
- `CATEGORIES` — list of category slugs
- `HUB_URLS` — mapping of category → hub page URL
- `MIN_LINKS` / `MAX_LINKS` — link count thresholds
- `STOP_WORDS` — words to exclude from keyword matching

## Integration with SemanticPipe

The linker can run standalone or be called from SemanticPipe via `--fix-links`.
When integrated, it runs after FAQ injection and opener hardening, ensuring
the FAQ section exists before the linker places "Related Research" above it.

## Output

Produces a summary report showing:
- Total articles, orphans found, articles fixed
- Links injected (hub links + related research links)
- Per-category breakdown
- Bottom 10 articles still needing manual attention

## Design Principles

Drawn from SEO best practices and the dragosroua/claude-content-skills
link-analyzer reference:

- **Orphan pages are critical** — zero inbound links means search engines
  may never discover the page. Fix these first.
- **Under-linked pages lack authority** — fewer than 3 inbound links means
  reduced crawl priority and lower perceived importance.
- **Respect topical silos** — same-category links are stronger signals than
  cross-category links. The hub-spoke architecture should be reinforced.
- **Contextual links > random links** — links should make sense to a reader.
  Topic matching ensures relevance.
- **Don't over-link** — more than ~50 outbound links dilutes equity. Keep
  injected links purposeful and limited.
