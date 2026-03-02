# DiggingScriptures — Project Context

## Overview
Static site at **diggingscriptures.com** built with Astro 5 + Tailwind 4 + React.
Deployed on Netlify (site ID: `18c0f63d-4335-4206-9a5b-13d5bb6d31b6`).
Git: `https://github.com/poolboy17/diggingscriptures.git` (branch: main)

## Content Structure
- **55 pilgrimage articles** in `src/content/pilgrimage/` (5 categories: context, places, routes, tips, faith)
- **680 research articles** in `src/content/research/` (5 categories below)
- Research categories: `biblical-archaeology`, `scripture`, `excavations`, `artifacts`, `faith`
- Hub pages at `/research/{category}` serve as silo landing pages

## SEO Pyramid Schema (frontmatter fields)
Every research article has these silo fields in YAML frontmatter:
```yaml
siloTier: "support"           # hub | pillar | cluster | support
siloCluster: "ark-covenant"   # cluster slug within category
siloParent: "/research/..."   # URL of parent (pillar or hub)
siloPriority: 53              # 1-100
```
- 55 pillar pages, 625 support pages, 64 clusters across 5 categories
- Pillar = longest article per cluster (>= 1500 words)

## Key Scripts (project root)
| Script | Purpose |
|--------|---------|
| `semantic-pipe-research.py` | SemanticPipe v2.1 — GEO/AEO/SXO optimization, FAQ injection, opener hardening, link fixing |
| `internal_linker.py` | Internal link analysis + silo-aware injection (v2). Flags: `--audit`, `--fix`, `--relink` |
| `silo_mapper.py` | SEO pyramid schema generator with auto-clustering. Flags: `--analyze`, `--apply`, `--export` |
| `_validate_pyramid.py` | Tests all pyramid linking chains (bottom-up + top-down) across every silo |

## Internal Linking Rules (enforced by internal_linker.py v2)
- Every support article links to its cluster pillar (via siloParent)
- Every support article links to its category hub
- Every pillar links to its category hub
- Every pillar links to cluster siblings (top-down)
- Cluster siblings cross-link to each other (avg >= 1 per article)
- Validated: 1424/1424 checks PASS across all 5 silos

## SemanticPipe Flags
```bash
python semantic-pipe-research.py --all                    # Full optimization
python semantic-pipe-research.py --all --fix-links        # + internal linking
python semantic-pipe-research.py --all --aeo-harden       # + FAQ injection
python semantic-pipe-research.py --all --fix-openers      # + opener hardening
python semantic-pipe-research.py --audit                  # Score audit only
python semantic-pipe-research.py --slug article-slug      # Single article
```

## Build & Deploy
```bash
cd /d D:\dev\projects\diggingscriptures
npx astro build                    # builds to dist/ (~752 pages, ~27s)
npx netlify deploy --prod --dir=dist --site=18c0f63d-4335-4206-9a5b-13d5bb6d31b6
```

## Windows CMD Notes
- Always use `shell: cmd` (not PowerShell) for python scripts
- Always set `PYTHONIOENCODING=utf-8` before running python
- For long operations (>30s), use .bat files with `start /b` pattern
- Git commits: use `-F filename` for multi-line messages (avoid inline quoting issues)

## Current SEO Scores (as of last full audit)
- GEO: 58.9%, AEO: 47.4%, SXO: 69.2%, Combined: 58.7%
- 19 D-grade articles still need manual attention

## Remaining TODO (lower priority)
- Google Analytics (GA4) + Search Console verification
- Custom 404 page
- Pagefind search integration
- Related articles component (render silo links in UI)
- Pagination for category pages
- Reading time + social share buttons
