# DiggingScriptures — Article Writer Config
# Version: 1.0 | Created: 2026-02-24
#
# USAGE: Writer config for diggingscriptures.com.
# Load this when generating content for this site.
# Note: This site has 5 distinct content types, each with its own schema and purpose.

---

# 1. SITE IDENTITY

**Site:** diggingscriptures.com
**Voice:** Scholarly explorer — rigorous, accessible, respectful of all faith traditions
**Audience:** Historically curious travelers, pilgrimage planners, people interested in the
intersection of faith, history, and place. NOT primarily devotional — this is for people
who want to understand, not just believe.
**Revenue model:** Affiliate tours (Viator/GYG) — ONLY in designated sections of places/routes
**Content directory:** `src/content/{hubs,stories,places,routes,context}/`
**File format:** Markdown (.md) with YAML frontmatter (schemas enforced by Astro collections)
**URL patterns:**
- Hubs: `/journeys/{hub-slug}/`
- Places: `/places/{place-slug}/`
- Routes: `/routes/{route-slug}/`
- Stories: `/stories/{story-slug}/`
- Context: `/context/{context-slug}/`

---

# 2. CONTENT ARCHITECTURE

## Hub/Spoke Model
```
Hubs (authority pages — define topics)
  ↕
Places (sacred sites and destinations)
  ↔
Routes (pilgrimage paths connecting places)
  ↔
Stories (people, traditions, cultural narratives)
  ↔
Context (historical and cultural background)
```

Every place, route, story, and context page links UP to its parent hub.
Hubs link DOWN to all their children. Cross-links between types are encouraged.

## Current Content (mostly placeholder — being built out)
- Hubs: 2 (christian-pilgrimage-traditions, faith-based-journeys)
- Stories: 1 (placeholder)
- Places: 3 (placeholders)
- Routes: 1 (placeholder)
- Context: 1 (placeholder)

---

# 3. CONTENT TYPE SCHEMAS

## 3A. HUBS (authority pages)
**Purpose:** Define a topic, link to all related content
**Monetization:** NEVER
**Word count:** 2,000-3,000 words
**Frontmatter:**
```yaml
---
title: "Title (≤70 chars)"
description: "Meta description (≤160 chars)"
lastUpdated: YYYY-MM-DD
topics:
  - topic-1
  - topic-2
relatedPlaces:
  - "place-slug"
relatedRoutes:
  - "route-slug"
draft: false
---
```

## 3B. PLACES (sacred sites and destinations)
**Purpose:** Deep-dive on a specific location
**Monetization:** OPTIONAL — only in "Experiencing This Place Today" section
**Word count:** 1,200-2,500 words
**Frontmatter:**
```yaml
---
title: "Title (≤70 chars)"
description: "Meta description (≤160 chars)"
region: "Geographic region"
country: "Country name"
coordinates:
  lat: 0.0
  lng: 0.0
faithTraditions:
  - Christianity
  - Judaism
placeType: "church|shrine|temple|mosque|monastery|natural-site|historical-site|pilgrimage-destination|other"
parentHub: "hub-slug"
relatedRoutes:
  - "route-slug"
hasExperienceSection: true/false
lastUpdated: YYYY-MM-DD
draft: false
---
```

## 3C. ROUTES (pilgrimage paths)
**Purpose:** Describe a pilgrimage route — history, path, and modern experience
**Monetization:** OPTIONAL — only in "Modern Pilgrimage Experiences" section
**Word count:** 1,200-2,500 words
**Frontmatter:**
```yaml
---
title: "Title (≤70 chars)"
description: "Meta description (≤160 chars)"
region: "Geographic region"
countries:
  - "Country 1"
  - "Country 2"
distanceKm: 790
typicalDurationDays: 30
faithTraditions:
  - Christianity
difficulty: "easy|moderate|challenging|difficult"
parentHub: "hub-slug"
placesOnRoute:
  - "place-slug-1"
  - "place-slug-2"
hasModernSection: true/false
lastUpdated: YYYY-MM-DD
draft: false
---
```

## 3D. STORIES (people, traditions, narratives)
**Purpose:** Tell the human story — a historical figure, a tradition, a legend
**Monetization:** NO
**Word count:** 1,000-2,000 words
**Frontmatter:**
```yaml
---
title: "Title (≤70 chars)"
description: "Meta description (≤160 chars)"
storyType: "historical-figure|tradition|cultural-practice|pilgrimage-account|legend|other"
faithTraditions:
  - Christianity
timePeriod: "1st century CE - Medieval period"
relatedPlaces:
  - "place-slug"
relatedRoutes:
  - "route-slug"
lastUpdated: YYYY-MM-DD
draft: false
---
```

## 3E. CONTEXT (background articles)
**Purpose:** Provide historical/cultural context that supports other content
**Monetization:** NEVER
**Word count:** 1,000-2,000 words
**Frontmatter:**
```yaml
---
title: "Title (≤70 chars)"
description: "Meta description (≤160 chars)"
contextType: "historical-background|cultural-overview|religious-context|geographical-context|terminology|other"
faithTraditions:
  - Christianity
regions:
  - "Mediterranean"
lastUpdated: YYYY-MM-DD
draft: false
---
```

---

# 4. WRITING RULES

## Voice and tone
- **Scholarly but accessible.** Write like a well-read historian giving a walking
  tour, not like a textbook. Show the evidence, name the sources, but keep the
  narrative compelling.
- **Respectful of all faith traditions.** This site covers Christianity, Judaism,
  Islam, Buddhism, Hinduism, and indigenous practices. Treat all traditions with
  equal scholarly rigor and respect. Never frame one tradition as "correct."
- **Evidence-based.** Distinguish clearly between documented history and
  tradition/legend. "According to tradition, James preached in Iberia" not
  "James preached in Iberia" (when historical evidence is thin).
- **Hedge appropriately.** Use "tradition holds that," "scholarship suggests,"
  "archaeological evidence indicates" — calibrate confidence to evidence quality.
- **Sensory where relevant.** When describing places and routes, include what
  a visitor would see, hear, and feel. The physical reality of pilgrimage matters.
- **No devotional language.** This is not a worship site. Avoid "blessed,"
  "sacred duty," "spiritual awakening" as editorial voice. It's fine to quote
  or describe others using such language.

## Content-type-specific rules

### Hubs
- Cover the topic comprehensively — this is the definitive page on the subject
- Link to every related place, route, story, and context page
- Structured as: overview → historical development → modern practice → related content
- NO affiliate content. These are pure authority pages.

### Places
- Open with the physical reality of the place — what it looks like, where it is
- Layer historical context chronologically
- If `hasExperienceSection: true`, include a final section "Experiencing [Place] Today"
  with practical visitor info. Affiliate links ONLY go in this section.
- If `hasExperienceSection: false`, keep it purely historical/cultural.

### Routes
- Open with the route's significance and basic stats (distance, duration, difficulty)
- Describe the path — key waypoints, terrain, what pilgrims experience
- Historical context: who walked it, when, why
- If `hasModernSection: true`, include "Modern Pilgrimage Experiences" with
  practical info. Affiliate links ONLY here.

### Stories
- Center on the human narrative — a person, a tradition, a legend
- Clearly distinguish documented history from legend/tradition
- Connect to specific places and routes where possible
- NO affiliate content. Ever.

### Context
- Pure background/reference material
- Can be more academic in tone than other types
- Must still be readable by a non-specialist
- NO affiliate content. Ever.

## Data density requirements
- ≥3 specific dates or time periods per article
- ≥3 named historical figures or scholars
- ≥2 named primary sources (books, inscriptions, archaeological evidence)
- At least 1 "the evidence suggests" or "scholarship indicates" hedge per article
- Places/routes: ≥3 practical details (distance, elevation, climate, best season)

## Answer Engine Optimization (AEO) requirements
These rules ensure content is extractable by featured snippets, AI answer boxes,
and generative search engines (Google AI Overviews, Perplexity, etc.).

### Opening paragraph rule
The first 1-2 sentences of every article MUST be a self-contained factual answer.
Write as if answering a direct question. Include a definitional verb (is, was, are,
refers to, dates to, represents) within the first sentence.
- ✅ "The Dead Sea Scrolls are a collection of Jewish texts discovered between 1947 and 1956 in caves near Qumran on the northwestern shore of the Dead Sea."
- ❌ "For centuries, scholars have debated the origins of some of the most important manuscripts ever found."

### Question-format headings
Include ≥2 question-format H2 or H3 headings per article. These directly target
People Also Ask boxes and AI answer extraction.
- ✅ `## What Evidence Supports the Exodus Narrative?`
- ✅ `### When Was the Temple of Solomon Built?`
- ❌ `## Evidence and Interpretation` (declarative — harder to extract)

### Definition sentences
Include ≥1 explicit "X is Y" definition sentence per major section. These are
snippet extraction targets.
- ✅ "Stratigraphy is the study of rock layers and their relative ages."
- ✅ "The Septuagint refers to the earliest Greek translation of the Hebrew Bible."

### Structured lists
Include ≥1 bulleted or numbered list per article. Lists are favored by answer
engines for "list snippets" — they display as expandable answer boxes.
- Key findings, notable artifacts, important dates, or chronological steps

### FAQ section (required for research articles)
Every research article MUST end with a `## Frequently Asked Questions` section
containing 3 Q&A pairs formatted as:
```markdown
## Frequently Asked Questions

### What is [topic]?
[2-3 sentence factual answer.]

### What evidence supports [claim]?
[2-3 sentence answer citing specific findings.]

### Why does [topic] matter for biblical studies?
[2-3 sentence answer connecting to broader significance.]
```

## Banned phrases
- journey (as metaphor — fine for literal pilgrimage journeys)
- unlock, game-changer, delve, realm, dive in
- furthermore, in conclusion, it's important to note
- sacred duty, spiritual awakening, blessed (as editorial voice)
- "the Holy Land" without qualification (specify whose holy land)

---

# 5. ARTICLE STRUCTURES

## Hub structure (2,000-3,000 words, 6-8 H2s)
```markdown
## [Overview — what is this topic]
[200-400 words. Define the topic. Historical roots.]

## [Historical development — early period]
[300-500 words. Origins, key figures, primary sources.]

## [Evolution — middle/modern period]
[300-500 words. How the tradition changed over time.]

## [Modern practice]
[200-400 words. What happens today. Who participates.]

## [Scholarly perspectives and debates]
[200-300 words. What historians/theologians disagree about.]

## [Related places and routes]
[200-300 words. Links to all child content. Brief intro to each.]

## [Further reading]
[100-200 words. Named books and sources for deeper study.]
```

## Place structure (1,200-2,500 words, 5-7 H2s)
```markdown
## [The place — physical description and significance]
[200-300 words. What it looks like. Why it matters.]

## [Historical layers — ancient through medieval]
[300-500 words. Who built it, who worshipped there, key events.]

## [The place in faith tradition(s)]
[200-400 words. What this place means to different traditions.]

## [Archaeological and scholarly evidence]
[200-300 words. What we know from physical evidence.]

## Experiencing [Place] Today (ONLY if hasExperienceSection: true)
[200-400 words. Practical visitor info. Affiliate links go here.]
```

## Route/Story/Context: follow similar patterns scaled to word count target.

---

# 6. INTERNAL LINKING RULES

- **Every spoke links UP to its parentHub** (places, routes, stories, context)
- **Hubs link DOWN to every child** they reference in relatedPlaces/relatedRoutes
- **Cross-type links encouraged:** a place should link to routes that pass through it,
  stories about people who visited, and context articles that explain the background
- **Minimum 3 internal links** per article (excluding hubs which need more)
- **Hubs: link to ALL related content** — no minimum/maximum, link comprehensively
- **Anchor text:** descriptive, 3-6 words
  - ✅ "the [Camino de Santiago route](/routes/camino-de-santiago/)"
  - ✅ "[Christian pilgrimage traditions](/journeys/christian-pilgrimage-traditions/) that shaped Europe"
  - ❌ "click here" / "read more"

---

# 7. QC CHECKLIST

### Frontmatter
- [ ] All required fields present for content type
- [ ] title ≤70 chars
- [ ] description ≤160 chars
- [ ] Content type-specific fields valid (storyType, placeType, etc.)
- [ ] parentHub references an existing hub (for places/routes)
- [ ] relatedPlaces/relatedRoutes reference existing slugs
- [ ] draft: false (unless intentionally drafting)

### Content quality
- [ ] Word count within range for content type
- [ ] ≥5 H2 sections (hubs: ≥6)
- [ ] ≥3 dates/time periods
- [ ] ≥3 named figures/scholars
- [ ] ≥2 primary source references
- [ ] History vs tradition clearly distinguished
- [ ] All faith traditions treated with equal respect
- [ ] Zero banned phrases
- [ ] No editorial devotional language

### AEO (Answer Engine Optimization)
- [ ] Opening paragraph is self-contained factual answer (definitional verb in sentence 1)
- [ ] ≥2 question-format H2 or H3 headings
- [ ] ≥1 definition sentence ("X is Y") per major section
- [ ] ≥1 bulleted or numbered list in article body
- [ ] FAQ section with 3 Q&A pairs at end of article (research articles)

### Monetization rules
- [ ] Hubs: ZERO affiliate links
- [ ] Stories: ZERO affiliate links
- [ ] Context: ZERO affiliate links
- [ ] Places: affiliate links ONLY in "Experiencing [Place] Today" section
- [ ] Routes: affiliate links ONLY in "Modern Pilgrimage Experiences" section

### Linking
- [ ] ≥3 internal links (non-hub content)
- [ ] Links to parentHub present
- [ ] Cross-type links where relevant
- [ ] All link paths match URL pattern for content type

---

# 8. CONTENT BRIEF INPUT FORMAT

```json
{
  "type": "content-brief",
  "site": "diggingscriptures",
  "slug": "target-slug",
  "contentType": "hubs|places|routes|stories|context",
  "parentHub": "hub-slug",
  "primaryKeyword": "primary search keyword",
  "secondaryKeywords": ["keyword 2", "keyword 3"],
  "requiredSubtopics": ["subtopic 1", "subtopic 2"],
  "requiredEntities": ["Historical Figure", "Place Name", "Primary Source"],
  "faithTraditions": ["Christianity", "Judaism"],
  "internalLinks": {
    "parentHub": "/journeys/hub-slug/",
    "relatedPlaces": ["/places/place-1/"],
    "relatedRoutes": ["/routes/route-1/"],
    "relatedStories": ["/stories/story-1/"]
  },
  "wordCountTarget": "1200-2500",
  "hasExperienceSection": true,
  "hasModernSection": false
}
```

---

END OF WRITER CONFIG
