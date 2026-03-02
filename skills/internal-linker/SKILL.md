---
name: internal-linker
description: >
  Automated internal link analysis, injection, and silo-aware relinking for
  static Markdown content sites. Use when the user wants to fix orphan pages,
  improve internal linking, enforce SEO pyramid structure, validate silo linking
  chains, increase link equity distribution, or relink articles using silo hierarchy.
  Works on Markdown source files with YAML frontmatter. Supports hub-spoke
  architectures with category-aware topic matching and silo-aware scoring (v2).
  Use this skill whenever the user mentions internal links, link building,
  orphan pages, link equity, silo structure, pyramid linking, or site structure.
---

# Internal Linker Skill (v2 — Silo-Aware)

## Purpose

Analyze and remediate internal linking across a static site's Markdown content.
Unlike analysis-only tools, this skill **fixes** linking gaps by injecting
contextual, topically-relevant internal links directly into article bodies.

**v2 adds silo-aware matching**: when `siloTier`, `siloCluster`, `siloParent`,
and `siloPriority` frontmatter fields are present, the linker uses them for
deterministic pyramid linking instead of relying solely on keyword heuristics.

## When to Use

- "Fix my internal linking" or "add more internal links"
- "Find orphan pages" or "which articles have no links?"
- "Relink articles using the silo structure"
- "Validate that every article links up to its pillar"
- "Run the pyramid validator"
- After bulk content migration (WordPress -> Astro, etc.)
- After running silo_mapper.py to assign pyramid tiers

## Architecture

### Phase 1: Inventory & Graph Build
Scans all Markdown files in the content directory. For each article, extracts:
- Existing internal links (regex: `[text](/path)` and `href="/path"`)
- Title, category, slug -> builds the URL each article lives at
- Title keywords and body keywords (stop-word filtered) for topic matching
- **Silo fields** (v2): `siloTier`, `siloCluster`, `siloParent`, `siloPriority`

Outputs: a link graph (source -> targets), per-article link counts, and silo metadata.

### Phase 2: Topic Matching (Silo-Aware Scoring v2)
For each article needing links, finds the best targets using a weighted algorithm:

**When silo fields are present (v2 mode):**
```
match_score = (
    5 x same_cluster_bonus           # strongest: deterministic grouping
  + 3 x target_is_pillar             # pillars are high-value targets
  + 1 x target_higher_priority       # prefer linking "up" the hierarchy
  + 1.5 x shared_title_keywords      # halved (0.5x of original 3)
  + 2 x same_category_bonus          # hub-spoke architecture respect
  + 0.5 x shared_body_keywords       # halved (0.5x of original 1)
  - 10 x already_linked_penalty      # don't duplicate existing links
)
```

**When silo fields absent (v1 fallback):**
```
match_score = (
    3 x shared_title_keywords
  + 2 x same_category_bonus
  + 1 x shared_body_keywords
  - 10 x already_linked_penalty
)
```

The pillar parent (from `siloParent`) is **guaranteed** to appear in the Related
Research section for support articles, ensuring every support page links to its
cluster authority.

### Phase 3: Link Injection
Two injection strategies, applied in order:

1. **Hub link** — If the article doesn't link to its category hub, prepend
   a contextual sentence after the first paragraph:
   `"This topic is part of our [research on {category}](/research/{category})."`

2. **Related Research section** — Append a `## Related Research` section
   before the FAQ section (if present) with 3-5 topically relevant links.
   In silo mode, pillar pages appear first, then cluster siblings.

The injector respects configurable minimum (default: 3) and maximum (default: 10).

## Usage

```bash
# Audit — report orphans, under-linked, and silo coverage
python internal_linker.py --audit

# Fix — inject links into under-linked articles only
python internal_linker.py --fix

# Relink — REPLACE all Related Research sections with silo-aware targets
python internal_linker.py --relink

# Relink single category
python internal_linker.py --relink --category biblical-archaeology

# Dry run any mode
python internal_linker.py --relink --dry-run
python internal_linker.py --fix --dry-run
```

## Silo Pyramid Schema (used by silo_mapper.py)

Frontmatter fields injected into every article by `silo_mapper.py`:

```yaml
siloTier: "support"                    # hub | pillar | cluster | support
siloCluster: "ark-covenant"            # cluster slug within category
siloParent: "/research/artifacts/..."  # parent URL (pillar or hub)
siloPriority: 53                       # 1-100 (higher = more authoritative)
```

**Tier hierarchy:**
- `hub` — category landing pages (e.g., /research/biblical-archaeology)
- `pillar` — longest/deepest article per cluster (>= 1500 words), priority 90-100
- `cluster` — reserved for future subtopic group pages
- `support` — individual articles, priority 10-80

**Linking rules enforced by v2:**
- Support -> Pillar: every support article links to its cluster pillar
- Support -> Hub: every support article links to its category hub
- Pillar -> Hub: every pillar links to its category hub
- Pillar -> Support: every pillar links to cluster siblings
- Intra-cluster: siblings link to each other (avg >= 1 cross-link per article)

## Pyramid Validation

Run `_validate_pyramid.py` to test all linking chains:
```bash
python _validate_pyramid.py
```

Tests per silo (5 tests x 5 silos = 25 test groups):
1. [BOTTOM-UP] Support -> Pillar
2. [BOTTOM-UP] Support -> Hub
3. [BOTTOM-UP] Pillar -> Hub
4. [TOP-DOWN]  Pillar -> Support
5. [COHESION]  Intra-cluster cross-linking

## Configuration

Edit constants at top of `internal_linker.py`:
- `RESEARCH_DIR` — path to Markdown content directory
- `CATEGORIES` — list of category slugs
- `HUB_URLS` — mapping of category -> hub page URL
- `MIN_LINKS` / `MAX_LINKS` — link count thresholds (default: 3/10)
- `TARGET_RELATED` — Related Research links per article (default: 4)

Edit constants at top of `silo_mapper.py`:
- `CONTENT_DIR` — path to content (site-agnostic, override per project)
- `MIN_CLUSTER_SIZE` — minimum articles to form a cluster (default: 3)
- `MAX_CLUSTERS_PER_CAT` — cap per category (default: 15)
- `PILLAR_THRESHOLD_WC` — word count for pillar status (default: 1500)

## Integration with SemanticPipe

The linker runs standalone or via SemanticPipe `--fix-links` flag.
When integrated, it runs as Step 6 (after opener hardening, before scoring).
Silo fields are read from frontmatter at inventory build time.

## Site-Agnostic Design

Both `internal_linker.py` and `silo_mapper.py` are designed to work on any
Markdown content site. To port to a new project:
1. Override `CONTENT_DIR`, `CATEGORIES`, `HUB_URLS` at top of each script
2. Run `silo_mapper.py --analyze` to verify clustering
3. Run `silo_mapper.py --apply` to inject frontmatter fields
4. Run `internal_linker.py --relink` for silo-aware linking
5. Run `_validate_pyramid.py` to confirm all chains pass
