#!/usr/bin/env python3
"""
SemanticPipe — Research Edition v2.0
Optimizes title, description, banned phrases, and computes semantic scores
for the 680 /research/ articles (biblical archaeology content).

v2.0 additions:
  - GEO (Generative Engine Optimization) scoring
  - AEO (Answer Engine Optimization) scoring
  - SXO (Search Experience Optimization) scoring
  - Combined multi-layer quality grade (A/B/C/D/F)

Usage:
  python semantic-pipe-research.py --all --force         # Optimize all
  python semantic-pipe-research.py --all --diff          # Preview changes
  python semantic-pipe-research.py --audit-only          # Score without changing
  python semantic-pipe-research.py --chunk 0 --chunks 4  # Process chunk 0 of 4
"""

import os, sys, re, json, copy, argparse, threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SPEC_VERSION = "DiggingScriptures-Research-2.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESEARCH_DIR = os.path.join(BASE_DIR, "src", "content", "research")
AUDIT_LOG = os.path.join(BASE_DIR, "SEMANTIC-AUDIT-RESEARCH.md")
AUDIT_JSON = os.path.join(BASE_DIR, "semantic-audit-research.jsonl")
audit_lock = threading.Lock()

CATEGORIES = ["biblical-archaeology", "scripture", "excavations", "artifacts", "faith"]

# Archaeology / biblical studies keywords
TOPIC_KEYWORDS = [
    "archaeology", "archaeological", "archaeologist", "excavation", "excavate",
    "artifact", "artefact", "ancient", "biblical", "bible", "scripture",
    "temple", "jerusalem", "dead sea", "scrolls", "inscription", "pottery",
    "testament", "hebrew", "greek", "tomb", "burial", "ruins", "discovery",
    "historical", "faith", "theology", "prophets", "covenant", "ark",
    "israel", "judah", "canaan", "mesopotamia", "egypt", "assyria",
    "babylon", "qumran", "jericho", "bethlehem", "nazareth", "galilee",
    "sacred", "church", "monastery", "shrine", "worship", "prayer",
    "scholars", "research", "evidence", "dating", "stratigraphy",
]

BANNED_PHRASES = [
    "in this article", "in this post", "in this guide",
    "without further ado", "it goes without saying",
    "needless to say", "at the end of the day",
    "it is important to note", "it is worth noting",
    "in today's world", "in today's day and age",
    "since the dawn of time", "throughout human history",
    "buckle up", "dive in", "let's dive",
    "game changer", "game-changer",
    "you won't believe", "mind-blowing",
]

BANNED_REPLACEMENTS = {
    "in this article": "", "in this post": "", "in this guide": "",
    "without further ado": "", "it goes without saying": "",
    "needless to say": "",
    "it is important to note": "Notably",
    "it is worth noting": "Notably",
}


# ── YAML Frontmatter Parser ─────────────────────────────────
def parse_frontmatter(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()
    if not raw.startswith("---"):
        return {}, raw, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw, raw
    yaml_str = parts[1].strip()
    body = parts[2]
    fm = {}
    current_key = None
    current_list = None
    for line in yaml_str.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if current_list is not None:
                val = stripped[2:].strip().strip('"').strip("'")
                current_list.append(val)
            continue
        if ":" in stripped:
            ci = stripped.index(":")
            key = stripped[:ci].strip()
            val = stripped[ci+1:].strip()
            if val == "":
                current_key = key
                current_list = []
                fm[key] = current_list
            elif val == "[]":
                fm[key] = []
                current_list = None
            else:
                val = val.strip('"').strip("'")
                if val.lower() == "true": val = True
                elif val.lower() == "false": val = False
                fm[key] = val
                current_list = None
    return fm, body, raw


def save_frontmatter(filepath, fm):
    """Surgically update title and description in the original file."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()
    if not raw.startswith("---"):
        return
    second_dash = raw.index("---", 3)
    fm_text = raw[3:second_dash]
    rest = raw[second_dash:]
    new_title = fm.get('title', '').replace('"', '\\"')
    fm_text = re.sub(r'^title:\s*".*?"$', f'title: "{new_title}"', fm_text, count=1, flags=re.MULTILINE)
    fm_text = re.sub(r'^title:\s*(?!")(.*?)$', f'title: "{new_title}"', fm_text, count=1, flags=re.MULTILINE)
    new_desc = fm.get('description', '').replace('"', '\\"')
    fm_text = re.sub(r'^description:\s*".*?"$', f'description: "{new_desc}"', fm_text, count=1, flags=re.MULTILINE)
    fm_text = re.sub(r'^description:\s*(?!")(.*?)$', f'description: "{new_desc}"', fm_text, count=1, flags=re.MULTILINE)
    result = "---" + fm_text + rest
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(result)


# ── Text Utilities ──────────────────────────────────────────
def strip_markdown(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def count_words(body):
    return len(strip_markdown(body).split())

def get_h2s(body):
    return re.findall(r'^##\s+(.+)$', body, re.MULTILINE)

def get_h3s(body):
    return re.findall(r'^###\s+(.+)$', body, re.MULTILINE)

def get_internal_links(body):
    return re.findall(r'\]\((/[^)]+)\)', body)

def get_paragraphs(body):
    plain = strip_markdown(body)
    return [p.strip() for p in plain.split('\n\n') if len(p.strip()) > 30]


# ── Title Optimizer (archaeology-tuned) ─────────────────────
def has_topic_keyword(title):
    t = title.lower()
    return any(kw in t for kw in TOPIC_KEYWORDS)

def optimize_title(title, category):
    changes = []
    original = title
    title = re.sub(r'(\w)S\b', r"\1's", title)
    if 30 <= len(title) <= 65 and has_topic_keyword(title):
        if title != original:
            changes.append(f"Title fix: '{original[:40]}' -> '{title[:40]}'")
        return title, changes
    if len(title) > 65:
        truncated = title[:65]
        last_space = truncated.rfind(' ')
        if last_space > 30:
            title = truncated[:last_space]
        else:
            title = truncated[:64]
    if len(title) < 30:
        suffix_map = {
            "biblical-archaeology": "Biblical Archaeology",
            "scripture": "Scripture Studies",
            "excavations": "Excavation & Discovery",
            "artifacts": "Ancient Artifacts",
            "faith": "Faith & Theology",
        }
        suffix = suffix_map.get(category, "Biblical Research")
        candidate = f"{title}: {suffix}"
        if len(candidate) <= 65:
            title = candidate
    if title != original:
        changes.append(f"Title: '{original[:40]}...' ({len(original)}c) -> '{title[:40]}...' ({len(title)}c)")
    return title, changes


# ── Description Optimizer ───────────────────────────────────
def optimize_description(desc, category, body=""):
    changes = []
    original = desc
    if 120 <= len(desc) <= 155:
        return desc, changes
    if len(desc) > 155:
        t = desc[:155]
        lp = t.rfind('.')
        if lp > 100:
            desc = t[:lp+1]
        else:
            ls = t.rfind(' ')
            desc = t[:ls].rstrip(',;:') + '.' if ls > 100 else t[:154] + '.'
    if len(desc) < 120 and body:
        plain = strip_markdown(body)
        paragraphs = [p.strip() for p in plain.split('\n\n') if len(p.strip()) > 80]
        if paragraphs:
            sentences = re.split(r'(?<=[.!?])\s+', paragraphs[0][:500])
            for s in sentences[:2]:
                s = s.strip()
                if len(s) < 20:
                    continue
                candidate = (desc.rstrip('.') + '. ' + s).strip()
                if len(candidate) <= 155:
                    desc = candidate
                    break
                elif len(candidate) > 155:
                    trimmed = candidate[:155]
                    ls = trimmed.rfind(' ')
                    if ls > 120:
                        desc = trimmed[:ls].rstrip('.,;:') + '.'
                    break
    if len(desc) < 120:
        pad_map = {
            "biblical-archaeology": " Explore archaeological evidence, methods, and discoveries that illuminate biblical history.",
            "scripture": " Examine ancient texts, translations, and the linguistic heritage of biblical manuscripts.",
            "excavations": " Discover key excavation sites, finds, and what they reveal about the ancient world.",
            "artifacts": " Learn about ancient artifacts, relics, and what archaeological finds tell us about biblical times.",
            "faith": " Explore the intersection of faith, theology, and archaeological evidence in biblical studies.",
        }
        pad = pad_map.get(category, " Explore biblical archaeology research and ancient discoveries.")
        candidate = desc.rstrip('.') + '.' + pad
        if len(candidate) > 155:
            candidate = candidate[:155]
            ls = candidate.rfind(' ')
            if ls > 120:
                candidate = candidate[:ls].rstrip('.,;:') + '.'
        if 120 <= len(candidate) <= 155:
            desc = candidate
    if desc != original:
        changes.append(f"Desc: {len(original)}c -> {len(desc)}c")
    return desc, changes


# ── Banned Phrase Fixer ─────────────────────────────────────
def fix_banned_phrases(body):
    changes = []
    for phrase in BANNED_PHRASES:
        pat = r'\b' + re.escape(phrase) + r'\b'
        if re.search(pat, body, re.I):
            repl = BANNED_REPLACEMENTS.get(phrase, '')
            body = re.sub(pat, repl, body, flags=re.I)
            changes.append(f"Removed '{phrase}'")
    return body, changes


# ═══════════════════════════════════════════════════════════════
# AEO HARDENING — Auto-inject FAQ + improve answer extractability
# ═══════════════════════════════════════════════════════════════

def generate_faq_from_title(title, category):
    """
    Generate 3 FAQ Q&A pairs from article title and category.
    Uses pattern-matched templates seeded by the title's topic.
    """
    # Extract the core subject from the title
    subject = title
    # Strip common prefixes
    for prefix in ['The ', 'A ', 'An ', 'How ', 'What ', 'Why ', 'When ', 'Where ', 'Who ']:
        if subject.startswith(prefix):
            subject = subject[len(prefix):]
            break

    category_labels = {
        'biblical-archaeology': 'biblical archaeology',
        'scripture': 'biblical manuscripts',
        'excavations': 'archaeological excavations',
        'artifacts': 'ancient artifacts',
        'faith': 'theological studies',
    }
    field = category_labels.get(category, 'biblical research')

    # Generate 3 question-answer templates based on patterns
    faqs = []

    # Q1: "What is..." definitional question
    faqs.append({
        'q': f"What is the significance of {subject.lower()} in {field}?",
        'a': f"{title} represents an important area of study within {field}. Scholars and researchers continue to examine the evidence surrounding this topic, drawing on archaeological findings, ancient texts, and historical records to deepen our understanding."
    })

    # Q2: "What evidence..." evidentiary question
    faqs.append({
        'q': f"What archaeological evidence relates to {subject.lower()}?",
        'a': f"Archaeological evidence related to {subject.lower()} includes material finds from excavation sites, inscriptions, pottery, and architectural remains. These physical discoveries help scholars evaluate historical claims and reconstruct the ancient context described in biblical and extra-biblical sources."
    })

    # Q3: "Why does... matter" relevance question
    faqs.append({
        'q': f"Why does {subject.lower()} matter for understanding the Bible?",
        'a': f"Understanding {subject.lower()} provides important context for interpreting biblical narratives. By examining the historical and archaeological background, readers gain a more grounded perspective on the people, places, and events described in scripture."
    })

    return faqs


def harden_aeo(body, title, category):
    """
    AEO hardening pass. Injects a FAQ section at the end of articles
    that don't already have one. Returns modified body and list of changes.
    """
    changes = []

    # Skip if article already has a FAQ section
    if re.search(r'^##\s+.*(?:FAQ|Frequently Asked|Common Questions)', body, re.MULTILINE | re.I):
        return body, changes

    # Generate FAQ
    faqs = generate_faq_from_title(title, category)

    # Build markdown FAQ section
    faq_md = "\n\n## Frequently Asked Questions\n"
    for faq in faqs:
        faq_md += f"\n### {faq['q']}\n\n{faq['a']}\n"

    # Append to body
    body = body.rstrip() + faq_md + "\n"
    changes.append("Injected FAQ section (3 Q&A pairs)")

    return body, changes


# ═══════════════════════════════════════════════════════════════
# v2.0 — MULTI-LAYER QUALITY SCORING (GEO / AEO / SXO)
# ═══════════════════════════════════════════════════════════════

def score_geo(body, plain, fm, wc):
    """
    GEO — Generative Engine Optimization
    Measures how well AI systems can extract, attribute, and cite this content.
    Factors: entity density, source references, structured claims, unique data.
    """
    score = 0
    details = []

    # 1. Named entities (people, places, orgs) — AI citation anchors
    entities = set()
    for m in re.finditer(r'\b([A-Z][a-z]+(?:\s+(?:of|the|and))?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', plain):
        entities.add(m.group(1))
    e_count = len(entities)
    if e_count >= 10: score += 3
    elif e_count >= 5: score += 2
    elif e_count >= 2: score += 1
    details.append(f"entities={e_count}")

    # 2. Source/attribution signals — AI engines prefer citable content
    src_pats = [r'\b(?:according to|records show|archives?|museum|documented)\b',
                r'\b(?:journal|court record|testimony|report|study|census)\b',
                r'\b(?:historian|researcher|archaeologist|professor|scholar)\b',
                r'\b(?:published|peer.reviewed|excavation report|field notes)\b',
                r'\b(?:university|institute|academic|dissertation|thesis)\b']
    src_count = sum(1 for p in src_pats if re.search(p, plain, re.I))
    if src_count >= 4: score += 3
    elif src_count >= 2: score += 2
    elif src_count >= 1: score += 1
    details.append(f"sources={src_count}")

    # 3. Specific dates/years — temporal anchors for factual claims
    years = {y for y in re.findall(r'\b([1-9]\d{2,3})\b', plain) if 100 <= int(y) <= 2030}
    if len(years) >= 5: score += 2
    elif len(years) >= 2: score += 1
    details.append(f"years={len(years)}")

    # 4. Quantitative data — measurements, statistics, specifics
    measurements = re.findall(r'\b\d+[\-\s](?:feet|miles?|meters?|km|pounds?|acres?|cubits?|inches?|cm)\b', plain, re.I)
    numbers = re.findall(r'\b\d{2,}\b', plain)
    data_density = (len(set(measurements)) + min(len(numbers), 20)) / max(wc/1000, 0.1)
    if data_density >= 8: score += 2
    elif data_density >= 3: score += 1
    details.append(f"data_density={data_density:.1f}")

    # 5. Unique factual claims — sentences with "is", "was", "were" + specifics
    factual = re.findall(r'[A-Z][^.!?]{20,}(?:is|was|were|dates? to|discovered in|built in|located in)[^.!?]{10,}[.!?]', plain)
    if len(factual) >= 10: score += 2
    elif len(factual) >= 4: score += 1
    details.append(f"factual_claims={len(factual)}")

    # 6. Image with alt text (AI uses image context for understanding)
    has_image = bool(fm.get('image'))
    has_alt = bool(fm.get('imageAlt'))
    if has_image and has_alt: score += 1
    details.append(f"image={'yes' if has_image else 'no'}")

    # Max possible: 14
    return {'score': score, 'max': 14, 'pct': round(score/14*100), 'details': details}


def score_aeo(body, plain, fm, wc):
    """
    AEO — Answer Engine Optimization
    Measures how well content can be extracted as direct answers by
    featured snippets, People Also Ask, and AI answer boxes.
    Factors: question-answer pairs, definition patterns, list structure.
    """
    score = 0
    details = []

    # 1. Question-answer patterns (Q in heading, A in first paragraph)
    h2s = get_h2s(body)
    question_h2s = [h for h in h2s if '?' in h or h.lower().startswith(('what', 'who', 'where', 'when', 'why', 'how'))]
    if len(question_h2s) >= 3: score += 3
    elif len(question_h2s) >= 1: score += 2
    elif any('?' in h for h in get_h3s(body)): score += 1
    details.append(f"question_headings={len(question_h2s)}")

    # 2. Definition patterns — "X is...", "X refers to..." (snippet bait)
    definitions = re.findall(r'(?:^|\. )[A-Z][a-z]+ (?:is|refers to|means|was|are) [a-z]', plain)
    if len(definitions) >= 5: score += 2
    elif len(definitions) >= 2: score += 1
    details.append(f"definitions={len(definitions)}")

    # 3. Opening paragraph quality — first 2 sentences should be self-contained answer
    paragraphs = get_paragraphs(body)
    if paragraphs:
        first_p = paragraphs[0]
        first_sentences = re.split(r'(?<=[.!?])\s+', first_p)[:2]
        opening = ' '.join(first_sentences)
        # Good opening: 40-200 chars, contains a factual statement
        if 40 <= len(opening) <= 200 and re.search(r'\b(?:is|was|are|were|dates?|located|discovered)\b', opening, re.I):
            score += 2
        elif len(opening) >= 40:
            score += 1
    details.append(f"opening_len={len(paragraphs[0]) if paragraphs else 0}")

    # 4. Structured lists (numbered or bulleted) — snippet-friendly format
    bullet_lines = len(re.findall(r'^[\s]*[-*+]\s', body, re.MULTILINE))
    numbered_lines = len(re.findall(r'^[\s]*\d+[.)]\s', body, re.MULTILINE))
    list_items = bullet_lines + numbered_lines
    if list_items >= 5: score += 2
    elif list_items >= 2: score += 1
    details.append(f"list_items={list_items}")

    # 5. Concise section structure (H2s that segment topic clearly)
    if len(h2s) >= 4: score += 2
    elif len(h2s) >= 2: score += 1
    details.append(f"h2s={len(h2s)}")

    # Max possible: 12
    return {'score': score, 'max': 12, 'pct': round(score/12*100), 'details': details}


def score_sxo(body, plain, fm, wc):
    """
    SXO — Search Experience Optimization
    Measures the reader journey quality: scannability, internal linking,
    content depth, and engagement signals.
    """
    score = 0
    details = []

    # 1. Internal links (keeps users on site, signals topic authority)
    internal_links = get_internal_links(body)
    if len(internal_links) >= 5: score += 3
    elif len(internal_links) >= 2: score += 2
    elif len(internal_links) >= 1: score += 1
    details.append(f"internal_links={len(internal_links)}")

    # 2. Content depth — word count sweet spot for authority articles
    if 1200 <= wc <= 3500: score += 3
    elif 800 <= wc < 1200: score += 2
    elif wc >= 600: score += 1
    details.append(f"wc={wc}")

    # 3. Heading hierarchy (H2 + H3 = scannability)
    h2s = get_h2s(body)
    h3s = get_h3s(body)
    heading_count = len(h2s) + len(h3s)
    if heading_count >= 6: score += 2
    elif heading_count >= 3: score += 1
    details.append(f"headings={heading_count}")

    # 4. Paragraph length distribution (no walls of text)
    paras = get_paragraphs(body)
    if paras:
        avg_para_len = sum(len(p.split()) for p in paras) / len(paras)
        long_paras = sum(1 for p in paras if len(p.split()) > 150)
        if avg_para_len <= 80 and long_paras == 0: score += 2
        elif avg_para_len <= 120 and long_paras <= 2: score += 1
        details.append(f"avg_para={avg_para_len:.0f}w,long={long_paras}")
    else:
        details.append("avg_para=N/A")

    # 5. Frontmatter completeness (title + desc + image + category)
    fm_fields = ['title', 'description', 'image', 'imageAlt', 'category', 'pubDate']
    present = sum(1 for f in fm_fields if fm.get(f))
    if present >= 5: score += 2
    elif present >= 3: score += 1
    details.append(f"fm_fields={present}/6")

    # Max possible: 12
    return {'score': score, 'max': 12, 'pct': round(score/12*100), 'details': details}


def compute_multilayer_grade(geo, aeo, sxo):
    """Combine GEO/AEO/SXO into a single A-F grade."""
    total = geo['score'] + aeo['score'] + sxo['score']
    max_total = geo['max'] + aeo['max'] + sxo['max']  # 38
    pct = round(total / max_total * 100)
    if pct >= 80: grade = 'A'
    elif pct >= 65: grade = 'B'
    elif pct >= 50: grade = 'C'
    elif pct >= 35: grade = 'D'
    else: grade = 'F'
    return {'grade': grade, 'total': total, 'max': max_total, 'pct': pct}


# ── Legacy Semantic Score (backward compat) ─────────────────
def compute_scores(body, plain, wc):
    entities = set()
    for m in re.finditer(r'\b([A-Z][a-z]+(?:\s+(?:of|the|and))?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', plain):
        entities.add(m.group(1))
    years = {y for y in re.findall(r'\b([1-9]\d{2,3})\b', plain) if 100 <= int(y) <= 2030}
    measurements = re.findall(r'\b\d+[\-\s](?:feet|miles?|meters?|km|pounds?|acres?)\b', plain, re.I)
    people = set()
    for m in re.finditer(r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\b', plain):
        name = m.group(1)
        skip = ['The ', 'This ', 'That ', 'These ', 'When ', 'Where ', 'What ', 'Which ']
        if not any(name.startswith(w) for w in skip):
            people.add(name)
    src_pats = [r'\b(?:according to|records show|archives?|museum|documented)\b',
                r'\b(?:journal|court record|testimony|report|study|census)\b',
                r'\b(?:historian|researcher|archaeologist|professor|scholar)\b']
    src_count = sum(1 for p in src_pats if re.search(p, plain, re.I))
    h2s = get_h2s(body)
    stop = {'that','this','with','from','what','when','where','were','have','been','they','into','also'}
    h2_words = {w for h in h2s for w in h.lower().split() if len(w) > 3 and w not in stop}
    return {
        'entities': len(entities), 'years': len(years),
        'dataPoints': len(set(measurements)), 'namedPeople': len(people),
        'sourceRefs': src_count, 'h2Breadth': len(h2_words),
        'entityDensity': round(len(entities) / max(wc/1000, 0.1), 1),
    }


# ── Inventory Loader ────────────────────────────────────────
def load_inventory():
    articles = {}
    for cat in CATEGORIES:
        cat_dir = os.path.join(RESEARCH_DIR, cat)
        if not os.path.isdir(cat_dir):
            continue
        for fname in sorted(os.listdir(cat_dir)):
            if not fname.endswith(".md"):
                continue
            slug = fname[:-3]
            filepath = os.path.join(cat_dir, fname)
            fm, body, raw = parse_frontmatter(filepath)
            articles[slug] = {
                "category": cat,
                "filepath": filepath,
                "fm": fm,
                "body": body,
            }
    return articles


# ── Core Optimizer (v2.0 with multi-layer scoring) ──────────
def optimize_article(slug, data, dry_run=False, show_diff=False, audit_only=False, aeo_harden=False):
    filepath = data['filepath']
    category = data['category']
    fm = copy.deepcopy(data['fm'])
    body = data['body']
    changes = []
    orig_title = fm.get('title', '')
    orig_desc = fm.get('description', '')

    if not audit_only:
        # 1. Title
        new_title, tc = optimize_title(fm.get('title', ''), category)
        if new_title != fm.get('title', ''):
            fm['title'] = new_title
        changes.extend(tc)

        # 2. Description
        new_desc, dc = optimize_description(fm.get('description', ''), category, body)
        if new_desc != fm.get('description', ''):
            fm['description'] = new_desc
        changes.extend(dc)

        # 3. Banned phrases
        body, bc = fix_banned_phrases(body)
        changes.extend(bc)

        # 4. AEO hardening — inject FAQ section if missing
        if aeo_harden:
            body, ac = harden_aeo(body, fm.get('title', ''), category)
            changes.extend(ac)

    # 5. Legacy semantic scores
    plain = strip_markdown(body)
    wc = count_words(body)
    scores = compute_scores(body, plain, wc)

    # 5. v2.0 multi-layer scores
    geo = score_geo(body, plain, fm, wc)
    aeo = score_aeo(body, plain, fm, wc)
    sxo = score_sxo(body, plain, fm, wc)
    grade = compute_multilayer_grade(geo, aeo, sxo)

    result = {
        'slug': slug, 'category': category,
        'changes': changes, 'scores': scores,
        'geo': geo, 'aeo': aeo, 'sxo': sxo, 'grade': grade,
        'title_len': len(fm.get('title', '')),
        'desc_len': len(fm.get('description', '')),
        'word_count': wc,
        'h2_count': len(get_h2s(body)),
    }

    if show_diff and changes:
        diffs = []
        if orig_title != fm.get('title', ''):
            diffs.append(f"  T: '{orig_title[:45]}' -> '{fm['title'][:45]}'")
        if orig_desc != fm.get('description', ''):
            diffs.append(f"  D: {len(orig_desc)}c -> {len(fm['description'])}c")
        result['diff'] = diffs

    if dry_run or audit_only:
        result['status'] = 'AUDIT' if audit_only else 'DRY_RUN'
        return result

    # Save
    save_frontmatter(filepath, fm)
    # Write body changes (banned phrase removal, FAQ injection, etc.)
    body_changed = any(('Removed' in c or 'Injected' in c) for c in changes)
    if body_changed:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()
        if raw.startswith("---"):
            idx = raw.index("---", 3)
            header = raw[:idx+3]
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(header + body)

    result['status'] = 'SAVED'
    # Audit log
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    entry = {'timestamp': now, 'slug': slug, 'category': category,
             'changes': changes, 'scores': scores,
             'geo': {'score': geo['score'], 'pct': geo['pct']},
             'aeo': {'score': aeo['score'], 'pct': aeo['pct']},
             'sxo': {'score': sxo['score'], 'pct': sxo['pct']},
             'grade': grade['grade'],
             'title_len': result['title_len'], 'desc_len': result['desc_len'],
             'word_count': wc}
    with audit_lock:
        with open(AUDIT_JSON, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return result


# ── Pipeline Runner (v2.0 with grade distribution) ──────────
def run_pipeline(slugs, articles, threads=4, dry_run=False, show_diff=False, audit_only=False, aeo_harden=False):
    print(f"\n{'='*70}")
    print(f"SemanticPipe v2.0 — Research Edition")
    mode = 'AUDIT' if audit_only else 'DRY' if dry_run else 'LIVE'
    if aeo_harden: mode += '+AEO'
    print(f"Articles: {len(slugs)} | Threads: {threads} | Mode: {mode}")
    print(f"{'='*70}\n")

    saved, errors = [], []
    start = datetime.now()

    def process(slug):
        try:
            return optimize_article(slug, articles[slug], dry_run, show_diff, audit_only, aeo_harden)
        except Exception as e:
            return {'slug': slug, 'status': 'ERROR', 'error': str(e), 'changes': [],
                    'grade': {'grade': '?', 'pct': 0}}

    with ThreadPoolExecutor(max_workers=threads) as ex:
        futures = {ex.submit(process, s): s for s in slugs}
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            s = r['slug']
            st = r['status']
            nc = len(r.get('changes', []))
            g = r.get('grade', {}).get('grade', '?')
            if st == 'ERROR':
                errors.append(r)
                print(f"  [{i:3d}/{len(slugs)}] ERR   {s[:45]:45s} {r.get('error','')[:30]}")
            else:
                saved.append(r)
                geo_p = r.get('geo', {}).get('pct', 0)
                aeo_p = r.get('aeo', {}).get('pct', 0)
                sxo_p = r.get('sxo', {}).get('pct', 0)
                detail = f"[{g}] GEO={geo_p}% AEO={aeo_p}% SXO={sxo_p}% {r.get('word_count',0)}w"
                if nc: detail += f" +{nc}chg"
                print(f"  [{i:3d}/{len(slugs)}] {st:5s} {s[:45]:45s} {detail}")
                if show_diff and r.get('diff'):
                    for d in r['diff']:
                        print(f"         {d}")

    elapsed = (datetime.now() - start).total_seconds()

    # ── Summary Report ──────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"DONE in {elapsed:.1f}s ({elapsed/max(len(slugs),1):.3f}s/article)")
    print(f"  Processed: {len(saved)} | Errors: {len(errors)}")

    if not saved:
        print(f"{'='*70}")
        return {'saved': 0, 'errors': len(errors), 'elapsed': elapsed}

    changed = [r for r in saved if r.get('changes')]
    print(f"  Articles changed: {len(changed)}")

    # Grade distribution
    grades = {}
    for r in saved:
        g = r.get('grade', {}).get('grade', '?')
        grades[g] = grades.get(g, 0) + 1
    print(f"\n  GRADE DISTRIBUTION:")
    for g in ['A', 'B', 'C', 'D', 'F']:
        count = grades.get(g, 0)
        bar = '#' * (count // 5) if count else ''
        print(f"    {g}: {count:3d} ({count/len(saved)*100:4.1f}%) {bar}")

    # Layer averages
    avg_geo = sum(r.get('geo', {}).get('pct', 0) for r in saved) / len(saved)
    avg_aeo = sum(r.get('aeo', {}).get('pct', 0) for r in saved) / len(saved)
    avg_sxo = sum(r.get('sxo', {}).get('pct', 0) for r in saved) / len(saved)
    avg_total = sum(r.get('grade', {}).get('pct', 0) for r in saved) / len(saved)
    print(f"\n  LAYER AVERAGES:")
    print(f"    GEO (AI citation):    {avg_geo:5.1f}%")
    print(f"    AEO (answer engine):  {avg_aeo:5.1f}%")
    print(f"    SXO (search UX):      {avg_sxo:5.1f}%")
    print(f"    COMBINED:             {avg_total:5.1f}%")

    # Legacy semantic averages
    avg_e = sum(r['scores']['entities'] for r in saved) / len(saved)
    avg_y = sum(r['scores']['years'] for r in saved) / len(saved)
    avg_p = sum(r['scores']['namedPeople'] for r in saved) / len(saved)
    avg_s = sum(r['scores']['sourceRefs'] for r in saved) / len(saved)
    print(f"\n  LEGACY SEMANTIC: entities={avg_e:.1f} years={avg_y:.1f} people={avg_p:.1f} sources={avg_s:.1f}")

    # Category breakdown
    print(f"\n  BY CATEGORY:")
    for cat in CATEGORIES:
        cat_arts = [r for r in saved if r.get('category') == cat]
        if cat_arts:
            avg_wc = sum(r.get('word_count', 0) for r in cat_arts) / len(cat_arts)
            avg_g = sum(r.get('grade', {}).get('pct', 0) for r in cat_arts) / len(cat_arts)
            cat_grades = {}
            for r in cat_arts:
                g = r.get('grade', {}).get('grade', '?')
                cat_grades[g] = cat_grades.get(g, 0) + 1
            dist = ' '.join(f"{g}={cat_grades.get(g,0)}" for g in ['A','B','C','D','F'] if cat_grades.get(g,0))
            print(f"    {cat:25s} {len(cat_arts):3d} articles  avg {avg_wc:.0f}w  {avg_g:.0f}%  {dist}")

    # Bottom 10 (lowest grades)
    bottom = sorted(saved, key=lambda r: r.get('grade', {}).get('pct', 0))[:10]
    print(f"\n  BOTTOM 10 (need improvement):")
    for r in bottom:
        g = r.get('grade', {}).get('grade', '?')
        pct = r.get('grade', {}).get('pct', 0)
        print(f"    [{g}] {pct:2d}% {r['slug'][:55]}")

    print(f"{'='*70}")
    if errors:
        print(f"\nErrors:")
        for r in errors:
            print(f"  {r['slug']}: {r.get('error', '')}")
    return {'saved': len(saved), 'errors': len(errors), 'elapsed': elapsed,
            'grades': grades, 'avg_geo': avg_geo, 'avg_aeo': avg_aeo, 'avg_sxo': avg_sxo}


# ── CLI Entry Point ─────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='SemanticPipe v2.0 — Research Edition')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--audit-only', action='store_true', help='Score only, no changes')
    parser.add_argument('--aeo-harden', action='store_true', help='Inject FAQ sections for AEO')
    parser.add_argument('--all', action='store_true', help='Process all articles')
    parser.add_argument('--force', action='store_true', help='Re-optimize everything')
    parser.add_argument('--diff', action='store_true', help='Show before/after')
    parser.add_argument('--threads', type=int, default=4, help='Thread count')
    parser.add_argument('--chunk', type=int, default=None, help='Chunk index (0-based)')
    parser.add_argument('--chunks', type=int, default=4, help='Total chunks')
    parser.add_argument('--category', type=str, default=None, help='Single category')
    args = parser.parse_args()

    print("Loading research inventory...")
    articles = load_inventory()
    print(f"  {len(articles)} articles across {len(CATEGORIES)} categories")
    for cat in CATEGORIES:
        c = sum(1 for a in articles.values() if a['category'] == cat)
        if c: print(f"    {cat}: {c}")

    # Determine targets
    if args.category:
        slugs = sorted(s for s, a in articles.items() if a['category'] == args.category)
    elif args.all or args.force or args.audit_only:
        slugs = sorted(articles.keys())
    else:
        print("Use --all, --force, --audit-only, or --category")
        sys.exit(0)

    # Chunking support
    if args.chunk is not None:
        chunk_size = len(slugs) // args.chunks
        remainder = len(slugs) % args.chunks
        start = args.chunk * chunk_size + min(args.chunk, remainder)
        end = start + chunk_size + (1 if args.chunk < remainder else 0)
        slugs = slugs[start:end]
        print(f"  Chunk {args.chunk}/{args.chunks}: articles {start}-{end-1} ({len(slugs)} articles)")

    if not slugs:
        print("No articles to process.")
        sys.exit(0)

    run_pipeline(slugs, articles, threads=args.threads,
                 dry_run=args.dry_run, show_diff=args.diff,
                 audit_only=args.audit_only, aeo_harden=args.aeo_harden)

if __name__ == '__main__':
    main()
