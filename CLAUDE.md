# DiggingScriptures — Project Context

## Site Identity
- **URL:** diggingscriptures.com
- **Stack:** Astro 5 + Tailwind 4 + React, static SSG, deployed on Netlify
- **Voice:** Scholarly explorer — rigorous, accessible, respectful of all faith traditions
- **Revenue:** Affiliate tours (Viator/GYG) — ONLY in designated sections of places/routes
- **Content dir:** `src/content/{hubs,stories,places,routes,context}/`
- **Format:** Markdown (.md) with YAML frontmatter + `<Fragment slot="">` sections

## Content Architecture (Hub-Spoke Model)
```
Hubs (authority pages — 2000-3000 words, NO monetization)
  ↕
Places (sacred sites — 1200-2500 words, affiliate in "Experience" section only)
  ↔
Routes (pilgrimage paths — 1200-2500 words, affiliate in "Modern" section only)
  ↔
Stories (people/traditions — 1000-2000 words, NO monetization)
  ↔
Context (background articles — 1000-2000 words, NO monetization)
```
## Content Inventory (Target: 42 articles)

### Hubs (5)
| Slug | Tradition | Status |
|------|-----------|--------|
| christian-pilgrimage-traditions | Christianity | DONE |
| faith-based-journeys | Multi-faith | DONE |
| islamic-pilgrimage-traditions | Islam | DONE |
| jewish-pilgrimage-heritage | Judaism | DONE |
| buddhist-pilgrimage-paths | Buddhism | DONE |

### Places (15)
| Slug | Hub | Status |
|------|-----|--------|
| jerusalem | christian | DONE |
| jerusalem-old-city | christian | DONE |
| santiago-de-compostela | christian | DONE |
| rome-vatican | christian | DONE |
| lourdes | christian | DONE |
| mecca | islamic | DONE |
| medina | islamic | IN PROGRESS |
| dome-of-the-rock | islamic | PENDING |
| western-wall | jewish | PENDING |
| safed-kabbalah | jewish | PENDING |
| hebron-cave-patriarchs | jewish | PENDING |
| bodh-gaya | buddhist | PENDING |
| lumbini | buddhist | PENDING |
| mount-koya | buddhist | PENDING |
| varanasi | faith-based | PENDING |
### Routes (8)
| Slug | Hub | Status |
|------|-----|--------|
| camino-de-santiago | christian | DONE |
| via-francigena | christian | PENDING |
| hajj-route | islamic | PENDING |
| abraham-path | faith-based | PENDING |
| shikoku-88-temples | buddhist | PENDING |
| kora-mount-kailash | buddhist | PENDING |
| st-olavs-way | christian | PENDING |
| kumano-kodo | buddhist | PENDING |

### Stories (8)
| Slug | Tradition | Status |
|------|-----------|--------|
| legend-of-saint-james | Christianity | DONE |
| helena-and-the-true-cross | Christianity | PENDING |
| ibn-battuta-pilgrim-traveler | Islam | PENDING |
| egeria-first-pilgrim-writer | Christianity | PENDING |
| margery-kempe-medieval-pilgrim | Christianity | PENDING |
| xuanzang-buddhist-pilgrim | Buddhism | PENDING |
| rabbi-nachman-journey-to-israel | Judaism | PENDING |
| kobo-daishi-shikoku | Buddhism | PENDING |

### Context (6)
| Slug | Type | Status |
|------|------|--------|
| history-of-christian-pilgrimage | historical-background | DONE |
| five-pillars-hajj-explained | religious-context | PENDING |
| three-pilgrim-festivals-judaism | religious-context | PENDING |
| four-sacred-sites-buddhism | religious-context | PENDING |
| relics-and-sacred-objects | cultural-overview | PENDING |
| pilgrimage-tourism-modern-era | cultural-overview | PENDING |
## Layout Slot Patterns

### Places: `<Fragment slot="history|culture|features|experience|related">`
### Routes: `<Fragment slot="history|journey|places|modern|related">`
### Stories: `<Fragment slot="narrative|context|legacy|related">`
### Context: default `<slot />` + `<slot name="concepts">` + `<slot name="sources">` + `<slot name="related">`
### Hubs: default `<slot />` (no fragments — plain markdown)

## Writing Rules (Key Points)
- Scholarly but accessible — like a historian giving a walking tour
- Respectful of ALL traditions equally — never frame one as "correct"
- Evidence-based: "tradition holds," "scholarship suggests," "archaeological evidence indicates"
- ≥3 dates, ≥3 named figures, ≥2 primary sources per article
- NO devotional language as editorial voice
- Banned: journey (as metaphor), unlock, game-changer, delve, realm, dive in, furthermore, in conclusion

## Key Files
- `docs/ARTICLE-WRITER-CONFIG.md` — Full 375-line writer config
- `CONTENT-MAP.md` — Complete content architecture
- `src/content/config.ts` — Astro collection schemas (LOCKED)
- `src/layouts/` — 7 layout templates (LOCKED)
- `netlify.toml` — Deployment config

## Research Silo
- **680 research articles** across 5 categories: biblical-archaeology (190), excavations (164), scripture (127), faith (119), artifacts (80)
- URL pattern: `/research/[category]/[slug]`
- Article JSON-LD schema on every research page (author, publisher, datePublished, image)
- Dynamic OG images per article (hero image instead of static default)
- Breadcrumbs on all layouts (Research, Story, Context)
- `/about` page with Organization schema for E-E-A-T

## SemanticPipe v2.0 (`semantic-pipe-research.py`)
Multi-threaded quality pipeline with three-layer scoring:
- **GEO** (Generative Engine Optimization) — entity density, source attribution, temporal anchors, factual claims
- **AEO** (Answer Engine Optimization) — question headings, definition patterns, opening paragraph, list structure, FAQ
- **SXO** (Search Experience Optimization) — internal links, content depth, heading hierarchy, paragraph length, frontmatter completeness
- Combined A/B/C/D/F grading per article
- `--audit-only` mode for scoring without changes
- `--aeo-harden` mode to auto-inject FAQ sections
- `--all --force` for full re-optimization

## Writing Rules (AEO-aware)
- Opening paragraph must be self-contained factual answer
- ≥2 question-format H2/H3 headings per article
- ≥1 definition sentence ("X is Y") per section
- ≥1 bulleted/numbered list per article
- FAQ section (3 Q&A pairs) required at end of every research article
- Full spec: `docs/ARTICLE-WRITER-CONFIG.md`