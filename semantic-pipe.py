#!/usr/bin/env python3
"""
SemanticPipe — DiggingScriptures Edition
Adapted from CursedTours SemanticPipe for Markdown+YAML frontmatter articles.

Usage:
  python semantic-pipe.py --all --diff          # Preview all changes
  python semantic-pipe.py --all --force         # Re-optimize everything
  python semantic-pipe.py --all --force --diff  # Re-optimize + show diffs
  python semantic-pipe.py --type places         # Optimize one content type
  python semantic-pipe.py --slugs jerusalem,mecca  # Specific articles
"""

import os, sys, re, math, json, argparse, copy, textwrap
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

SPEC_VERSION = "DiggingScriptures-1.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(BASE_DIR, "src", "content")
AUDIT_LOG = os.path.join(BASE_DIR, "SEMANTIC-AUDIT-LOG.md")
AUDIT_JSON = os.path.join(BASE_DIR, "semantic-audit.jsonl")
audit_lock = threading.Lock()

# Content types and their URL path prefixes
CONTENT_TYPES = ["hubs", "places", "routes", "stories", "context"]
# Map content type dir → URL prefix (Astro uses /journeys/ for hubs)
TYPE_URL_MAP = {
    "hubs": "journeys",
    "places": "places",
    "routes": "routes",
    "stories": "stories",
    "context": "context",
}

# DiggingScriptures hub slugs
HUB_SLUGS = {
    "faith-based-journeys",
    "christian-pilgrimage-traditions",
    "islamic-pilgrimage-traditions",
    "jewish-pilgrimage-heritage",
    "buddhist-pilgrimage-paths",
}

# Pilgrimage / faith keywords for title optimization
PILGRIMAGE_KEYWORDS = [
    "pilgrimage", "pilgrim", "sacred", "faith", "holy", "spiritual",
    "religious", "devotion", "shrine", "temple", "church", "mosque",
    "synagogue", "monastery", "medieval", "ancient", "journey",
    "prayer", "worship", "saint", "prophet", "biblical", "liturgical",
]

# Banned phrases (filler/SEO spam) — body only
BANNED_PHRASES = [
    "in this article", "in this post", "in this guide",
    "without further ado", "it goes without saying",
    "needless to say", "at the end of the day",
    "it is important to note", "it is worth noting",
    "in today's world", "in today's day and age",
    "since the dawn of time", "throughout human history",
    "from time immemorial", "since time immemorial",
    "buckle up", "dive in", "let's dive",
    "game changer", "game-changer",
    "the ultimate guide", "everything you need to know",
    "you won't believe", "mind-blowing",
]

BANNED_REPLACEMENTS = {
    "in this article": "",
    "in this post": "",
    "in this guide": "",
    "without further ado": "",
    "it goes without saying": "",
    "needless to say": "",
    "it is important to note": "Notably",
    "it is worth noting": "Notably",
}


# ============================================================
# YAML FRONTMATTER PARSER
# ============================================================
def parse_frontmatter(filepath):
    """Parse a Markdown file with YAML frontmatter.
    Returns (frontmatter_dict, body_text, raw_content).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    # Split on --- delimiters
    if not raw.startswith("---"):
        return {}, raw, raw

    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw, raw

    yaml_str = parts[1].strip()
    body = parts[2]

    # Simple YAML parser (handles our frontmatter without PyYAML dep)
    fm = {}
    current_key = None
    current_list = None

    for line in yaml_str.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # List item
        if stripped.startswith("- "):
            if current_list is not None:
                val = stripped[2:].strip().strip('"').strip("'")
                current_list.append(val)
            continue

        # Key: value pair
        if ":" in stripped:
            colon_idx = stripped.index(":")
            key = stripped[:colon_idx].strip()
            val = stripped[colon_idx + 1:].strip()

            if val == "":
                # Could be start of a list or nested object
                current_key = key
                current_list = []
                fm[key] = current_list
            elif val == "[]":
                fm[key] = []
                current_key = key
                current_list = None
            else:
                # Scalar value
                val = val.strip('"').strip("'")
                if val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                else:
                    try:
                        val = int(val)
                    except ValueError:
                        try:
                            val = float(val)
                        except ValueError:
                            pass
                fm[key] = val
                current_key = key
                current_list = None

    return fm, body, raw


def save_frontmatter(filepath, fm, body):
    """Surgically update only title and description in the original file.
    Preserves all other frontmatter exactly as-is to avoid YAML mangling.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    if not raw.startswith("---"):
        return

    # Find the frontmatter boundaries
    second_dash = raw.index("---", 3)
    fm_text = raw[3:second_dash]
    rest = raw[second_dash:]  # includes closing --- and body

    # Surgically replace title line
    new_title = fm.get('title', '')
    safe_title = new_title.replace('"', '\\"')
    fm_text = re.sub(
        r'^title:\s*".*?"$',
        f'title: "{safe_title}"',
        fm_text, count=1, flags=re.MULTILINE
    )
    # Also handle unquoted titles
    fm_text = re.sub(
        r"^title:\s*(?!\")(.*?)$",
        f'title: "{safe_title}"',
        fm_text, count=1, flags=re.MULTILINE
    )

    # Surgically replace description line
    new_desc = fm.get('description', '')
    safe_desc = new_desc.replace('"', '\\"')
    fm_text = re.sub(
        r'^description:\s*".*?"$',
        f'description: "{safe_desc}"',
        fm_text, count=1, flags=re.MULTILINE
    )
    # Also handle unquoted descriptions
    fm_text = re.sub(
        r"^description:\s*(?!\")(.*?)$",
        f'description: "{safe_desc}"',
        fm_text, count=1, flags=re.MULTILINE
    )

    result = "---" + fm_text + rest
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(result)


# ============================================================
# TEXT UTILITIES
# ============================================================
def strip_markdown(text):
    """Strip Markdown formatting to get plain text."""
    # Remove Fragment slot tags
    text = re.sub(r'<Fragment\s+slot="[^"]*"\s*>', '', text)
    text = re.sub(r'</Fragment>', '', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    # Remove links but keep text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove images
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    # Collapse whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def count_words(body):
    """Count words in the Markdown body (excludes frontmatter)."""
    plain = strip_markdown(body)
    return len(plain.split())


def get_h2s(body):
    """Extract H2 headings from Markdown body."""
    return re.findall(r'^##\s+(.+)$', body, re.MULTILINE)


def get_internal_links(body):
    """Extract internal link targets from Markdown body."""
    # Markdown links: [text](/type/slug/) or [text](/type/slug)
    links = re.findall(r'\]\(/([\w-]+)/([\w-]+)/?\)', body)
    return links  # list of (type, slug) tuples


def get_body_before_slots(body):
    """Get body content, stripping Fragment slot wrappers."""
    # Remove Fragment tags but keep content
    text = re.sub(r'<Fragment\s+slot="[^"]*"\s*>', '', body)
    text = re.sub(r'</Fragment>', '', text)
    return text


# ============================================================
# INVENTORY LOADER
# ============================================================
def load_inventory():
    """Load all articles across all content types.
    Returns (all_articles, type_map, slug_to_title, slug_to_type).
    - all_articles: dict of slug -> {type, filepath, fm, body}
    - type_map: dict of content_type -> [slugs]
    - slug_to_title: dict of slug -> title
    - slug_to_type: dict of slug -> content_type
    """
    all_articles = {}
    type_map = {t: [] for t in CONTENT_TYPES}
    slug_to_title = {}
    slug_to_type = {}

    for ctype in CONTENT_TYPES:
        cdir = os.path.join(CONTENT_DIR, ctype)
        if not os.path.isdir(cdir):
            continue
        for fname in sorted(os.listdir(cdir)):
            if not fname.endswith(".md"):
                continue
            slug = fname[:-3]  # strip .md
            filepath = os.path.join(cdir, fname)
            fm, body, raw = parse_frontmatter(filepath)
            all_articles[slug] = {
                "type": ctype,
                "filepath": filepath,
                "fm": fm,
                "body": body,
                "raw": raw,
            }
            type_map[ctype].append(slug)
            slug_to_title[slug] = fm.get("title", slug)
            slug_to_type[slug] = ctype

    return all_articles, type_map, slug_to_title, slug_to_type


# ============================================================
# TITLE & DESCRIPTION OPTIMIZERS
# ============================================================
def has_pilgrimage_keyword(title):
    """Check if title contains at least one pilgrimage/faith keyword."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in PILGRIMAGE_KEYWORDS)


def optimize_title(title, slug, content_type):
    """Ensure title is 30-60 chars and contains a pilgrimage keyword.
    Returns (new_title, changes).
    """
    changes = []
    original = title

    # If already good length and has keyword, return as-is
    if 30 <= len(title) <= 60 and has_pilgrimage_keyword(title):
        return title, changes

    # Title too short — enrich with context (try progressively longer suffixes)
    if len(title) < 30:
        suffix_tiers = [
            {  # Tier 1: longest
                "hubs": "Sacred Pilgrimage Traditions",
                "places": "Sacred Pilgrimage Destination",
                "routes": "Historic Pilgrimage Route",
                "stories": "A Pilgrimage Story",
                "context": "Pilgrimage History & Context",
            },
            {  # Tier 2: medium
                "hubs": "Pilgrim Traditions Guide",
                "places": "Sacred Pilgrimage Site",
                "routes": "Pilgrimage Route Guide",
                "stories": "Pilgrimage Story",
                "context": "Pilgrimage History",
            },
            {  # Tier 3: short
                "hubs": "Pilgrim Traditions",
                "places": "Sacred Site Guide",
                "routes": "Pilgrim Route",
                "stories": "Pilgrim's Story",
                "context": "Faith & Pilgrimage",
            },
        ]
        for tier in suffix_tiers:
            suffix = tier.get(content_type, "Pilgrimage Guide")
            candidate = f"{title}: {suffix}"
            if 30 <= len(candidate) <= 60:
                title = candidate
                break
        # Last resort if still short
        if len(title) < 30:
            candidate = f"{title} — Sacred Pilgrimage Guide"
            if len(candidate) <= 60:
                title = candidate

    # Title too long — trim at sentence/word boundary
    if len(title) > 60:
        truncated = title[:60]
        last_space = truncated.rfind(' ')
        if last_space > 30:
            title = truncated[:last_space]
        else:
            title = truncated[:59]

    # Still missing keyword? Try to add one
    if not has_pilgrimage_keyword(title) and len(title) < 50:
        # Add keyword based on content type
        kw_map = {
            "places": "Sacred",
            "routes": "Pilgrimage",
            "stories": "Pilgrim",
            "context": "Sacred",
            "hubs": "Pilgrimage",
        }
        kw = kw_map.get(content_type, "Sacred")
        candidate = f"{title} — {kw} Guide"
        if len(candidate) <= 60:
            title = candidate

    if title != original:
        changes.append(f"Title: '{original}' ({len(original)}c) -> '{title}' ({len(title)}c)")

    return title, changes


def optimize_description(desc, slug, content_type, body=""):
    """Ensure description is 120-155 chars.
    Auto-enriches thin descriptions using first paragraph of article body.
    Returns (new_desc, changes).
    """
    changes = []
    original = desc

    if 120 <= len(desc) <= 155:
        return desc, changes

    # Too long — trim at sentence boundary
    if len(desc) > 155:
        truncated = desc[:155]
        last_period = truncated.rfind('.')
        if last_period > 100:
            desc = truncated[:last_period + 1]
        else:
            last_space = truncated.rfind(' ')
            if last_space > 100:
                desc = truncated[:last_space].rstrip(',;:') + '.'
            else:
                desc = truncated[:154] + '.'

    # Too short — auto-enrich from body content
    if len(desc) < 120 and body:
        # Extract first substantive paragraph from body
        plain = strip_markdown(body)
        paragraphs = [p.strip() for p in plain.split('\n\n') if len(p.strip()) > 80]
        if paragraphs:
            first_para = paragraphs[0]
            # Extract first sentence
            sentences = re.split(r'(?<=[.!?])\s+', first_para)
            # Try appending first sentence to existing desc
            if sentences:
                first_sent = sentences[0].strip()
                # If description doesn't end with period, add one
                base = desc.rstrip('.')
                # Try combining: existing desc + distilled sentence
                if len(first_sent) > 30:
                    # Trim first sentence to fit
                    available = 155 - len(base) - 2  # 2 for ". "
                    if available > 20:
                        trimmed = first_sent[:available]
                        last_sp = trimmed.rfind(' ')
                        if last_sp > 20:
                            trimmed = trimmed[:last_sp]
                        candidate = f"{base}. {trimmed.rstrip('.,;:') + '.'}"
                        if 120 <= len(candidate) <= 155:
                            desc = candidate
                        elif len(candidate) > 155:
                            # Trim to fit
                            desc = candidate[:155]
                            ls = desc.rfind(' ')
                            if ls > 120:
                                desc = desc[:ls].rstrip('.,;:') + '.'

        # If still short after enrichment, try type-specific padding
        if len(desc) < 120:
            padding_map = {
                "places": " Discover the history, traditions, and spiritual significance of this sacred pilgrimage destination.",
                "routes": " Explore the history, stages, and spiritual meaning of this ancient pilgrimage route.",
                "stories": " Discover the historical narrative and lasting impact on pilgrimage traditions worldwide.",
                "context": " Explore the historical roots, cultural significance, and enduring traditions of sacred travel.",
                "hubs": " A comprehensive guide to the sacred journeys, destinations, and traditions of this faith.",
            }
            padding = padding_map.get(content_type, " Explore the sacred history and spiritual traditions of pilgrimage.")
            candidate = desc.rstrip('.') + '.' + padding
            if len(candidate) > 155:
                candidate = candidate[:155]
                ls = candidate.rfind(' ')
                if ls > 120:
                    candidate = candidate[:ls].rstrip('.,;:') + '.'
            if 120 <= len(candidate) <= 155:
                desc = candidate

    if desc != original:
        changes.append(f"Description: '{original[:40]}...' ({len(original)}c) -> '{desc[:40]}...' ({len(desc)}c)")

    return desc, changes


# ============================================================
# BANNED PHRASE FIXER
# ============================================================
def fix_banned_phrases(body):
    """Replace banned phrases in body. Returns (new_body, changes)."""
    changes = []
    plain_lower = strip_markdown(body).lower()

    for phrase in BANNED_PHRASES:
        pat = r'\b' + re.escape(phrase) + r'\b'
        if re.search(pat, plain_lower, re.I):
            replacement = BANNED_REPLACEMENTS.get(phrase, '')
            def replace_match(m):
                original = m.group(0)
                if original[0].isupper() and replacement:
                    return replacement[0].upper() + replacement[1:]
                return replacement
            new_body = re.sub(
                r'\b' + re.escape(phrase) + r'\b',
                replace_match, body, flags=re.I
            )
            if new_body != body:
                changes.append(f"Replaced banned '{phrase}'")
                body = new_body

    return body, changes


# ============================================================
# INTERNAL LINK CHECKER
# ============================================================
def check_internal_links(body, all_slugs, slug_to_type):
    """Check internal links in body. Returns (link_count, broken_links, self_links, slug)."""
    links = re.findall(r'\]\(/([\w-]+)/([\w-]+)/?\)', body)
    total = len(links)
    broken = []
    for link_type, link_slug in links:
        if link_slug not in all_slugs:
            broken.append(f"/{link_type}/{link_slug}/")
    return total, broken


# ============================================================
# SEMANTIC SCORE COMPUTER
# ============================================================
def compute_semantic_scores(body, plain_text, word_count):
    """Compute I1-I7 semantic scores from Markdown content."""

    # I1: Named entities — places, institutions, events
    entities = set()
    for m in re.finditer(
        r'\b([A-Z][a-z]+(?:\s+(?:of|the|and|de|du|la|le|von|van)\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
        plain_text
    ):
        entities.add(m.group(1))
    entity_count = len(entities)

    # I2: Unique years cited
    years = set(re.findall(r'\b([1-9]\d{2,3})\b', plain_text))
    # Filter to plausible years (100-2030)
    years = {y for y in years if 100 <= int(y) <= 2030}
    year_count = len(years)

    # I3: Data points (dates, measurements, specific numbers)
    full_dates = re.findall(
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
        plain_text
    )
    measurements = re.findall(
        r'\b\d+[\-\s](?:feet|foot|miles?|yards?|meters?|kilometres?|kilometers?|km|pounds?|tons?|acres?|square)\b',
        plain_text, re.I
    )
    specific_nums = re.findall(r'\b\d{2,}\b', plain_text)
    data_count = len(set(full_dates)) + len(set(measurements)) + min(len(specific_nums), 20)

    # I4: Named people
    people = set()
    for m in re.finditer(
        r'\b([A-Z][a-z]{2,}\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\b',
        plain_text
    ):
        name = m.group(1)
        skip_words = ['The ', 'This ', 'That ', 'These ', 'Those ', 'When ', 'Where ',
                       'What ', 'Which ', 'Their ', 'After ', 'Before ', 'During ']
        if not any(name.startswith(w) for w in skip_words):
            people.add(name)
    people_count = len(people)

    # I5: Source/authority references
    source_patterns = [
        r'\b(?:according to|records show|archives?|historical society|museum|documented)\b',
        r'\b(?:newspaper|journal|court record|testimony|report|investigation|survey|study|census)\b',
        r'\b(?:historian|researcher|archaeologist|professor|curator|scholar|author|chronicler)\b',
    ]
    src_count = sum(1 for p in source_patterns if re.search(p, plain_text, re.I))

    # I6: H2 topic breadth
    h2s = get_h2s(body)
    h2_words = set()
    stop_words = {'that','this','with','from','what','when','where','were','have','been',
                  'they','them','their','into','also','than','more','most','some','other'}
    for h in h2s:
        for w in h.lower().split():
            if len(w) > 3 and w not in stop_words:
                h2_words.add(w)
    h2_breadth = len(h2_words)

    # I7: Entity density
    ent_density = round(entity_count / max(word_count / 1000, 0.1), 1)

    return {
        'entities': entity_count,
        'years': year_count,
        'dataPoints': data_count,
        'namedPeople': people_count,
        'sourceRefs': src_count,
        'h2Breadth': h2_breadth,
        'entityDensity': ent_density,
    }


# ============================================================
# SELF-VALIDATOR
# ============================================================
def validate_article(slug, fm, body, all_slugs, slug_to_type, content_type):
    """Run all BLOCK and WARN checks. Returns (results, block_fails, warn_fails)."""
    results = []
    block_fails = []
    warn_fails = []
    plain = strip_markdown(body)
    wc = len(plain.split())
    clean_body = get_body_before_slots(body)

    def check(tier, cid, name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        results.append((tier, cid, name, status, detail))
        if not passed:
            if tier == 'BLOCK':
                block_fails.append(cid)
            else:
                warn_fails.append(cid)

    # --- BLOCK checks ---
    # B2: Title length
    tlen = len(fm.get('title', ''))
    check('WARN', 'B2', 'Title 30-60 chars', 30 <= tlen <= 60, f"{tlen} chars")

    # B3: Description length
    dlen = len(fm.get('description', ''))
    check('WARN', 'B3', 'Description 120-155 chars', 120 <= dlen <= 155, f"{dlen} chars")

    # B4: No H1 in body (## is H2 in Markdown, # is H1)
    h1_count = len(re.findall(r'^#\s+', body, re.MULTILINE))
    check('BLOCK', 'B4', 'No H1 in body', h1_count == 0)

    # B5: H2 count 4-8 (or up to 16 for 2000+ word articles)
    h2_count = len(get_h2s(body))
    max_h2 = 16 if wc >= 2000 else 8
    check('WARN', 'B5', 'H2 count 4-8', 4 <= h2_count <= max_h2,
          f"{h2_count} H2s (max {max_h2} for {wc}w)")

    # B6: Word count >= 1000 (skip for hubs which can be shorter)
    min_words = 500 if content_type == "hubs" else 1000
    check('BLOCK', 'B6', f'Word count >={min_words}', wc >= min_words, str(wc))

    # B7: Banned phrases
    plain_lower = plain.lower()
    found_banned = []
    for b in BANNED_PHRASES:
        if re.search(r'\b' + re.escape(b) + r'\b', plain_lower, re.I):
            found_banned.append(b)
    check('BLOCK', 'B7', 'No banned phrases', not found_banned,
          str(found_banned) if found_banned else "")

    # B9: Internal body links >= 3
    link_count, broken = check_internal_links(body, all_slugs, slug_to_type)
    check('WARN', 'B9', '>=3 body links', link_count >= 3, f"{link_count} links")

    # B10: No self-links
    self_pattern = f'](/{TYPE_URL_MAP.get(content_type, content_type)}/{slug}'
    has_self = self_pattern in body
    check('BLOCK', 'B10', 'No self-links', not has_self)

    # B11: No broken internal links
    check('BLOCK', 'B11', 'No broken links', not broken,
          str(broken) if broken else "")

    # B12: Keyword in title
    title_lower = fm.get('title', '').lower()
    keyword_in_title = has_pilgrimage_keyword(fm.get('title', ''))
    check('WARN', 'B12', 'Pilgrimage keyword in title', keyword_in_title)

    # B13: Keyword in first 100 words
    first100 = ' '.join(plain.split()[:100]).lower()
    kw_in_first100 = any(kw in first100 for kw in PILGRIMAGE_KEYWORDS)
    check('WARN', 'B13', 'Keyword in first 100w', kw_in_first100)

    # B14: Featured image
    has_image = bool(fm.get('image', ''))
    has_alt = bool(fm.get('imageAlt', ''))
    check('WARN', 'B14', 'Image + alt text', has_image and has_alt,
          f"image={'yes' if has_image else 'MISSING'} alt={'yes' if has_alt else 'MISSING'}")

    # B14f: Image file exists
    if has_image:
        img_path = os.path.join(BASE_DIR, 'public', fm['image'].lstrip('/'))
        check('WARN', 'B14f', 'Image file exists', os.path.exists(img_path),
              fm['image'] if not os.path.exists(img_path) else '')

    return results, block_fails, warn_fails


# ============================================================
# AUDIT LOGGER
# ============================================================
def write_audit_log(slug, results, changes, block_count, warn_count, scores):
    """Thread-safe append to SEMANTIC-AUDIT-LOG.md."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    rows = ""
    for tier, cid, name, status, detail in results:
        d = f" ({detail})" if detail else ""
        rows += f"| {tier} | {cid} | {name} | {status}{d} |\n"

    info_rows = ""
    for key, label in [
        ('entities', 'I1 Entities'), ('years', 'I2 Years'),
        ('dataPoints', 'I3 Data points'), ('namedPeople', 'I4 Named people'),
        ('sourceRefs', 'I5 Source refs'), ('h2Breadth', 'I6 H2 breadth'),
        ('entityDensity', 'I7 Entity density')
    ]:
        val = scores.get(key, 'N/A')
        info_rows += f"| INFO | {label.split()[0]} | {label} | {val} |\n"

    changes_md = '\n'.join(f"- {c}" for c in changes) if changes else "- No changes needed"

    entry = f"""
## [{now}] — Optimization Run
**Operator:** SemanticPipe-DS (automated)
**Article:** {slug}
**Spec version:** {SPEC_VERSION}

### Validation Results
| Tier | ID | Check | Result |
|------|----|-------|--------|
{rows}{info_rows}
### Changes Made
{changes_md}

### Block fails: {block_count} | Warn fails: {warn_count}
"""
    with audit_lock:
        with open(AUDIT_LOG, 'a', encoding='utf-8') as f:
            f.write(entry)
        json_entry = {
            'timestamp': now,
            'slug': slug,
            'spec_version': SPEC_VERSION,
            'block_count': block_count,
            'warn_count': warn_count,
            'changes': changes,
            'checks': {cid: status for tier, cid, name, status, detail in results},
            'semantic_scores': scores,
        }
        with open(AUDIT_JSON, 'a', encoding='utf-8') as f:
            f.write(json.dumps(json_entry, ensure_ascii=False) + '\n')


# ============================================================
# CORE OPTIMIZER — processes a single article
# ============================================================
def optimize_article(slug, article_data, all_slugs, slug_to_title, slug_to_type,
                     dry_run=False, show_diff=False):
    """Optimize a single article. Returns dict with status, changes, etc."""
    filepath = article_data['filepath']
    content_type = article_data['type']
    fm = copy.deepcopy(article_data['fm'])
    body = article_data['body']
    changes = []

    # Snapshot for diff
    orig_fm = copy.deepcopy(fm)
    orig_body = body

    # --- OPTIMIZE ---

    # 1. Optimize title (B2, B12)
    new_title, title_changes = optimize_title(
        fm.get('title', ''), slug, content_type
    )
    if new_title != fm.get('title', ''):
        fm['title'] = new_title
    changes.extend(title_changes)

    # 2. Optimize description (B3)
    new_desc, desc_changes = optimize_description(
        fm.get('description', ''), slug, content_type, body
    )
    if new_desc != fm.get('description', ''):
        fm['description'] = new_desc
    changes.extend(desc_changes)

    # 3. Fix banned phrases (B7)
    body, banned_changes = fix_banned_phrases(body)
    changes.extend(banned_changes)

    # 4. Compute semantic scores
    plain = strip_markdown(body)
    wc = count_words(body)
    scores = compute_semantic_scores(body, plain, wc)

    # --- VALIDATE ---
    results, block_fails, warn_fails = validate_article(
        slug, fm, body, all_slugs, slug_to_type, content_type
    )
    block_count = len(block_fails)
    warn_count = len(warn_fails)

    result = {
        'slug': slug,
        'type': content_type,
        'block_fails': block_fails,
        'warn_fails': warn_fails,
        'block_count': block_count,
        'warn_count': warn_count,
        'changes': changes,
        'scores': scores,
        'title_len': len(fm.get('title', '')),
        'desc_len': len(fm.get('description', '')),
        'word_count': wc,
        'h2_count': len(get_h2s(body)),
        'link_count': len(get_internal_links(body)),
    }

    # Show diff
    if show_diff and changes:
        diff_lines = []
        if orig_fm.get('title') != fm.get('title'):
            diff_lines.append(f"  title: '{orig_fm.get('title','')[:50]}' -> '{fm.get('title','')[:50]}'")
        if orig_fm.get('description') != fm.get('description'):
            diff_lines.append(f"  desc: {len(orig_fm.get('description',''))}c -> {len(fm.get('description',''))}c")
        if diff_lines:
            result['diff'] = diff_lines

    if dry_run:
        result['status'] = 'DRY_RUN'
        return result

    # --- SAVE (only if 0 BLOCK fails) ---
    if block_count == 0:
        save_frontmatter(filepath, fm, body)
        result['status'] = 'SAVED'
    else:
        result['status'] = 'BLOCKED'

    # --- LOG ---
    write_audit_log(slug, results, changes, block_count, warn_count, scores)

    return result


# ============================================================
# PIPELINE RUNNER
# ============================================================
def run_pipeline(target_slugs, all_articles, all_slugs, slug_to_title, slug_to_type,
                 threads=4, dry_run=False, show_diff=False):
    """Run the optimizer across multiple articles."""
    print(f"\n{'='*70}")
    print(f"SemanticPipe — DiggingScriptures Edition")
    print(f"Spec: {SPEC_VERSION}")
    print(f"Articles: {len(target_slugs)} | Threads: {threads} | Dry run: {dry_run}")
    print(f"{'='*70}\n")

    saved = []
    blocked = []
    errors = []
    start_time = datetime.now()

    def process_one(slug):
        try:
            return optimize_article(
                slug, all_articles[slug], all_slugs, slug_to_title, slug_to_type,
                dry_run, show_diff
            )
        except Exception as e:
            import traceback
            return {'slug': slug, 'status': 'ERROR', 'error': str(e),
                    'traceback': traceback.format_exc()}

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(process_one, s): s for s in target_slugs}
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            slug = result['slug']
            status = result['status']

            if status in ('SAVED', 'DRY_RUN'):
                saved.append(result)
                icon = 'OK' if status == 'SAVED' else 'DRY'
                detail = f"{len(result.get('changes',[]))} changes, {result.get('warn_count',0)}w"
                detail += f" | t={result.get('title_len',0)}c d={result.get('desc_len',0)}c"
                detail += f" | {result.get('word_count',0)}w {result.get('h2_count',0)}h2 {result.get('link_count',0)}lnk"
            elif status == 'BLOCKED':
                blocked.append(result)
                icon = 'BLOCK'
                detail = f"fails: {result['block_fails']}"
            else:
                errors.append(result)
                icon = 'ERR'
                detail = result.get('error', 'unknown')

            print(f"  [{i:3d}/{len(target_slugs)}] {icon:5s} {slug[:45]:45s} {detail}")
            if show_diff and result.get('diff'):
                for dl in result['diff']:
                    print(f"         {dl}")

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n{'='*70}")
    print(f"PIPELINE COMPLETE")
    print(f"{'='*70}")
    print(f"  Duration:  {elapsed:.1f}s ({elapsed/max(len(target_slugs),1):.2f}s/article)")
    print(f"  Saved:     {len(saved)}")
    print(f"  Blocked:   {len(blocked)}")
    print(f"  Errors:    {len(errors)}")

    # Semantic score summary
    if saved:
        avg_ent = sum(r['scores']['entities'] for r in saved) / len(saved)
        avg_yrs = sum(r['scores']['years'] for r in saved) / len(saved)
        avg_ppl = sum(r['scores']['namedPeople'] for r in saved) / len(saved)
        avg_src = sum(r['scores']['sourceRefs'] for r in saved) / len(saved)
        avg_h2b = sum(r['scores']['h2Breadth'] for r in saved) / len(saved)
        print(f"\n  Avg Semantic Scores:")
        print(f"    Entities: {avg_ent:.1f}  Years: {avg_yrs:.1f}  People: {avg_ppl:.1f}")
        print(f"    Sources: {avg_src:.1f}  H2 Breadth: {avg_h2b:.1f}")

    # Title/desc summary
    short_titles = [r for r in saved if r.get('title_len', 0) < 30]
    long_titles = [r for r in saved if r.get('title_len', 0) > 60]
    thin_descs = [r for r in saved if r.get('desc_len', 0) < 120]
    long_descs = [r for r in saved if r.get('desc_len', 0) > 155]
    low_links = [r for r in saved if r.get('link_count', 0) < 3]

    if short_titles or long_titles or thin_descs or long_descs:
        print(f"\n  Remaining Issues:")
        if short_titles:
            print(f"    Short titles (<30c): {len(short_titles)} — {[r['slug'] for r in short_titles[:5]]}")
        if long_titles:
            print(f"    Long titles (>60c): {len(long_titles)} — {[r['slug'] for r in long_titles[:5]]}")
        if thin_descs:
            print(f"    Thin descriptions (<120c): {len(thin_descs)} — {[r['slug'] for r in thin_descs[:5]]}")
        if long_descs:
            print(f"    Long descriptions (>155c): {len(long_descs)} — {[r['slug'] for r in long_descs[:5]]}")
        if low_links:
            print(f"    Low links (<3): {len(low_links)} — {[r['slug'] for r in low_links[:5]]}")

    print(f"{'='*70}")

    if blocked:
        print(f"\nBLOCKED articles:")
        for r in blocked:
            print(f"  {r['slug']}: {r['block_fails']}")
    if errors:
        print(f"\nERROR articles:")
        for r in errors:
            print(f"  {r['slug']}: {r.get('error','unknown')}")

    return {
        'total': len(target_slugs),
        'saved': len(saved),
        'blocked': len(blocked),
        'errors': len(errors),
        'elapsed': elapsed,
        'results': saved + blocked + errors,
    }


# ============================================================
# CLI ENTRY POINT
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='SemanticPipe — DiggingScriptures Edition')
    parser.add_argument('--dry-run', action='store_true', help='Report without saving')
    parser.add_argument('--slugs', type=str, help='Comma-separated article slugs')
    parser.add_argument('--type', type=str, help='Optimize one content type (hubs/places/routes/stories/context)')
    parser.add_argument('--threads', type=int, default=4, help='Thread pool size')
    parser.add_argument('--all', action='store_true', help='Optimize all articles')
    parser.add_argument('--force', action='store_true', help='Re-optimize even if passing')
    parser.add_argument('--diff', action='store_true', help='Show before/after diffs')
    args = parser.parse_args()

    # Load inventory
    print("Loading article inventory...")
    all_articles, type_map, slug_to_title, slug_to_type = load_inventory()
    all_slugs = set(all_articles.keys())
    total = sum(len(v) for v in type_map.values())
    print(f"  {total} articles across {len([t for t in type_map if type_map[t]])} content types")
    for t in CONTENT_TYPES:
        if type_map[t]:
            print(f"    {t}: {len(type_map[t])} articles")

    # Determine targets
    if args.slugs:
        target_slugs = [s.strip() for s in args.slugs.split(',')]
        for s in target_slugs:
            if s not in all_slugs:
                print(f"ERROR: Unknown slug '{s}'")
                sys.exit(1)
    elif args.type:
        if args.type not in CONTENT_TYPES:
            print(f"ERROR: Unknown type '{args.type}'. Choose from: {CONTENT_TYPES}")
            sys.exit(1)
        target_slugs = type_map[args.type]
    elif args.all:
        target_slugs = sorted(all_slugs)
    else:
        print("No target specified. Use --slugs, --type, or --all")
        sys.exit(0)

    if not target_slugs:
        print("No articles to optimize.")
        sys.exit(0)

    # Run pipeline
    summary = run_pipeline(
        target_slugs, all_articles, all_slugs, slug_to_title, slug_to_type,
        threads=args.threads, dry_run=args.dry_run, show_diff=args.diff
    )

    if summary['errors'] > 0:
        sys.exit(2)
    elif summary['blocked'] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
