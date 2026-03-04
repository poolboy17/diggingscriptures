# SemanticPipe — SEO Optimization Spec (DiggingScriptures)
# Version: 1.0 | Created: 2026-03-02
#
# This is the single source of truth for what "optimized" means.
# The audit script tests against these criteria.
# Cowork logs its work against these criteria.
# Google decides if we got it right.

---

# 1. PURPOSE

This spec defines the measurable requirements an article must meet
to be considered "SEO-optimized" under the SemanticPipe pipeline.

DiggingScriptures has TWO content arms:
- **Pilgrimage content** (42 articles across 5 collections: hubs/places/routes/stories/context)
- **Research content** (680 articles across 5 categories: biblical-archaeology/scripture/excavations/artifacts/faith)

Each arm has different schemas, word targets, and linking rules.
The audit script handles both.

---

# 2. STRUCTURAL REQUIREMENTS (hard pass/fail)

These are non-negotiable. Every article must pass all of these.

## 2A. All Articles (pilgrimage + research)

| # | Requirement | Test | Threshold |
|---|------------|------|-----------|
| S1 | Valid Markdown | Parses YAML frontmatter without error | — |
| S2 | Title present | `title` in frontmatter | non-empty |
| S3 | Title length | Character count | ≤70 |
| S4 | Description present | `description` in frontmatter | non-empty |
| S5 | Description length | Character count | ≤160 |
| S6 | No H1 in body | Absence of `# ` at start of line in body | 0 |
| S7 | H2 count | Count `## ` headings | ≥4 |
| S8 | Word count floor | Strip markdown, count words | varies by type (see §2B/2C) |
| S9 | No banned phrases | Text search against banned list | 0 matches |
| S10 | draft: false | Article is published | true |
| S11 | No mojibake | Search for encoding artifacts (â€, Ã, etc.) | 0 |

## 2B. Pilgrimage Articles (by collection)

| Collection | Word count | H2 count | Extra required fields |
|-----------|-----------|---------|----------------------|
| hubs | ≥2,000 | ≥6 | topics |
| places | ≥1,200 | ≥5 | region, country, parentHub |
| routes | ≥1,200 | ≥5 | region, countries, parentHub |
| stories | ≥1,000 | ≥4 | storyType, faithTraditions |
| context | ≥1,000 | ≥4 | contextType |

## 2C. Research Articles

| # | Requirement | Test | Threshold |
|---|------------|------|-----------|
| RS1 | category field | Present, valid enum | one of 5 categories |
| RS2 | siloTier field | Present | hub/pillar/cluster/support |
| RS3 | siloCluster field | Present | non-empty |
| RS4 | siloParent field | Present | valid URL path |
| RS5 | Word count — pillar | Strip markdown, count words | ≥1,500 |
| RS6 | Word count — support | Strip markdown, count words | ≥800 |

---

# 3. INTERNAL LINKING REQUIREMENTS (hard pass/fail)

## 3A. Pilgrimage Articles

| # | Requirement | Test | Threshold |
|---|------------|------|-----------|
| PL1 | Body internal links | Count markdown links `[text](/path/)` | ≥3 |
| PL2 | Parent hub link | Link to `/journeys/{parentHub}/` in body | ≥1 (if parentHub set) |
| PL3 | Cross-type links | Links to other collections (places↔routes↔stories) | ≥1 |
| PL4 | Cross-link validity | Every internal href resolves to a content file | 0 broken |
| PL5 | No self-links | Article does not link to its own URL | 0 |

## 3B. Research Articles (silo-enforced)

| # | Requirement | Test | Threshold |
|---|------------|------|-----------|
| RL1 | Body internal links | Count markdown links | ≥2 |
| RL2 | Category hub link | Link to `/research/{category}/` | ≥1 |
| RL3 | Silo parent link | Link matching siloParent path | ≥1 (support/cluster tier) |
| RL4 | Cross-link validity | Every internal href resolves to a content file | 0 broken |
| RL5 | No self-links | Article does not link to its own URL | 0 |

---

# 4. SEO ON-PAGE REQUIREMENTS (hard pass/fail)

| # | Requirement | Test | Threshold |
|---|------------|------|-----------|
| P1 | AEO opener | First sentence contains definitional verb (is, was, are, refers to, dates to) | present |
| P2 | Question-format headings | H2 or H3 that starts with What/When/Where/Who/Why/How/Can/Did/Does/Is | ≥2 |
| P3 | Definition sentence | At least 1 "X is Y" / "X refers to" pattern in body | ≥1 |
| P4 | Structured list | At least 1 bulleted or numbered list in body | ≥1 |
| P5 | FAQ section (research only) | `## Frequently Asked Questions` with ≥3 H3 sub-questions | present |

---

# 5. SEMANTIC DEPTH SIGNALS (measured, thresholds recommended)

| # | Signal | How measured | Threshold | Notes |
|---|--------|-------------|-----------|-------|
| D1 | Named entities | Count capitalized multi-word phrases | ≥5 per article | People, places, institutions |
| D2 | Unique years cited | Distinct 4-digit years (200-2030) | ≥3 per article | Historical grounding |
| D3 | Named people/scholars | Specific historical figures, researchers | ≥3 per article | Per writer config |
| D4 | Source/authority refs | Books, archives, inscriptions, archaeological evidence | ≥2 per article | Primary source requirement |
| D5 | H2 topic breadth | Unique content words across all H2 headings | ≥8 unique terms | Topical diversity |
| D6 | Entity density | Named entities per 1,000 words | ≥3.0 per 1k | Normalized depth metric |
| D7 | Faith tradition balance | No single tradition framed as "correct" | manual | Per writer config |
| D8 | Evidence hedging | ≥1 "tradition holds" / "scholarship suggests" / "evidence indicates" | ≥1 per article | Distinguishes history from tradition |

---

# 6. WHAT "OPTIMIZED" MEANS

An article is considered **optimized** when:

1. **All structural requirements pass** — zero fails
2. **All linking requirements pass** — zero fails
3. **All on-page SEO requirements pass** — zero fails
4. **All semantic depth signals meet thresholds** — zero below minimum

An article is **partially optimized** when:
- Structural and linking requirements pass
- But 1-2 semantic signals fall below threshold

An article is **unoptimized** when:
- Any structural requirement fails, OR
- 3+ semantic signals fall below threshold

---

# 7. WHAT "OPTIMIZED" DOES NOT MEAN

- It does NOT mean Google will rank it. Google decides.
- It does NOT mean the content is subjectively "good."
- It does NOT guarantee competitor parity.
- These criteria are necessary conditions, not sufficient conditions.

---

# 8. BANNED PHRASES

Tested by the audit script. Zero tolerance.

```
journey (metaphorical only — literal pilgrimage "journey" is fine)
unlock
game-changer
delve
realm
dive in
furthermore
in conclusion
it's important to note
sacred duty
spiritual awakening
blessed (as editorial voice — quoting others is fine)
```

Additional context: "the Holy Land" without qualification is flagged as a warning,
not a hard fail. Specify whose holy land when possible.

---

# 9. AUDIT PROCESS

When running an optimization audit:

1. **Run the audit script** (`audit.py`) — produces structural + semantic scorecard
2. **Log every action** — Cowork must write an `AUDIT-LOG.md` recording:
   - Timestamp of audit start/end
   - Number of articles scanned (pilgrimage vs research breakdown)
   - Summary scorecard (pass/fail/warning counts)
   - List of articles that fail any requirement, with specific failures
   - List of articles below semantic thresholds, with specific signals
   - Any actions taken (fixes applied, articles re-optimized)
   - Any actions deferred (with reason)
3. **Persist the report** — `AUDIT-REPORT.md` stays in the repo as the latest snapshot
4. **Compare to previous** — note improvements/regressions

---

# 10. COWORK LOGGING REQUIREMENTS

Every Cowork session that touches article content MUST produce:

**File: `AUDIT-LOG.md`** (append-only, never overwrite)

Each entry:
```
## [YYYY-MM-DD HH:MM] — [Session Type]
**Operator:** Cowork / [role name]
**Scope:** [which articles, how many, pilgrimage/research]
**Actions taken:**
- [article-slug]: [what was changed and why]
**Results:**
- Articles modified: N
- Structural fixes: N
- Semantic improvements: N
- Deferred: N (reason)
**Audit score before:** [if available]
**Audit score after:** [run audit.py, paste summary]
```

---

# 11. CONTENT ARM PRIORITIES

## Research (680 articles) — HIGH PRIORITY
- WordPress import, quality varies wildly
- Many articles are thin AI-generated content from early 2024
- Silo structure is in place but linking may be incomplete
- Already has semantic-pipe-research.py for batch optimization
- Focus: structural fixes, AEO hardening, link validation

## Pilgrimage (42 articles) — MEDIUM PRIORITY
- Mostly placeholder or newly written content
- Clean architecture, needs content buildout
- Focus: writing new articles per CONTENT-MAP.md, then audit

---

# 12. VERSIONING

- This spec: `SEO-OPTIMIZATION-SPEC.md` v1.0
- Audit script: `audit.py` (to be created)
- Audit report: `AUDIT-REPORT.md` (generated, timestamped)
- Audit log: `AUDIT-LOG.md` (append-only history)
- Writer config: `docs/ARTICLE-WRITER-CONFIG.md` v1.0

Changes to thresholds or requirements increment the spec version.
The audit script must match the spec version it tests against.

---

END OF SPEC
