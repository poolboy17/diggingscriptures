#!/usr/bin/env python3
"""
DiggingScriptures SEO Audit — v1.0
Tests against SEO-OPTIMIZATION-SPEC.md v1.0
Usage: python audit.py [--research-only] [--pilgrimage-only] [--verbose]
"""
import os, re, sys, json, glob, datetime
from pathlib import Path
from collections import Counter

ROOT = Path(r"D:\dev\projects\diggingscriptures")
CONTENT = ROOT / "src" / "content"

# ── Banned phrases ──────────────────────────────────────────────
BANNED = [
    "game-changer", "delve", "realm", "dive in",
    "furthermore", "in conclusion", "it's important to note",
    "sacred duty", "spiritual awakening",
]
# "unlock" and "journey" need context — checked separately
BANNED_RE = re.compile("|".join(re.escape(b) for b in BANNED), re.IGNORECASE)
UNLOCK_RE = re.compile(r"\bunlock\b", re.IGNORECASE)
JOURNEY_META_RE = re.compile(r"\bjourney\b", re.IGNORECASE)  # flag metaphorical only
MOJIBAKE_RE = re.compile(r"â€|Ã©|Ã¨|Ã¼|Ã¶|Ã¤|â€™|â€œ|â€\x9d|Â")

# ── YAML parser (simple, no pyyaml dependency) ──────────────────
def parse_frontmatter(text):
    """Extract YAML frontmatter as dict + body as string."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    yaml_block = text[3:end].strip()
    body = text[end+3:].strip()
    fm = {}
    current_key = None
    current_list = None
    for line in yaml_block.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # List item
        if stripped.startswith("- "):
            val = stripped[2:].strip().strip('"').strip("'")
            if current_list is not None:
                current_list.append(val)
            continue
        # Key: value
        m = re.match(r'^(\w[\w\-]*):\s*(.*)', stripped)
        if m:
            key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
            current_key = key
            if val == "":
                current_list = []
                fm[key] = current_list
            else:
                current_list = None
                # Type coercion
                if val.lower() in ("true", "false"):
                    fm[key] = val.lower() == "true"
                elif re.match(r'^\d+$', val):
                    fm[key] = int(val)
                elif re.match(r'^\d+\.\d+$', val):
                    fm[key] = float(val)
                else:
                    fm[key] = val
        # Nested object (coordinates, etc.) — skip for now
    return fm, body

# ── Text analysis helpers ───────────────────────────────────────
def strip_markdown(text):
    """Remove markdown syntax, return plain text."""
    t = re.sub(r'!\[.*?\]\(.*?\)', '', text)      # images
    t = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', t)  # links → text
    t = re.sub(r'[#*_`~>]', '', t)                # formatting
    t = re.sub(r'\s+', ' ', t)
    return t.strip()

def count_words(text):
    plain = strip_markdown(text)
    return len(plain.split())

def count_h2(body):
    return len(re.findall(r'^##\s+', body, re.MULTILINE))

def count_h3(body):
    return len(re.findall(r'^###\s+', body, re.MULTILINE))

def has_h1(body):
    return bool(re.search(r'^#\s+[^#]', body, re.MULTILINE))

def get_h2_texts(body):
    return [m.strip() for m in re.findall(r'^##\s+(.+)$', body, re.MULTILINE)]

def get_internal_links(body):
    """Return list of (anchor_text, path) for internal links."""
    return re.findall(r'\[([^\]]*)\]\((/[^\)]*)\)', body)

def count_named_entities(text):
    plain = strip_markdown(text)
    caps = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', plain)
    return len(set(caps))

def count_unique_years(text):
    years = set(re.findall(r'\b([12]\d{3})\b', text))
    # Also catch BCE/CE years like "3rd century B.C."
    years |= set(re.findall(r'\b(\d{1,2}(?:st|nd|rd|th)\s+century)', text, re.IGNORECASE))
    return len(years)

def count_source_refs(text):
    patterns = [
        r'\bCodex\b', r'\bManuscript\b', r'\bScroll[s]?\b',
        r'\barchaeolog', r'\bexcavat', r'\binscription',
        r'\baccording to\b', r'\bscholarship\b', r'\breveal',
        r'\brevise', r'\bProfessor\b', r'\bDr\.\b',
        r'\buniversity\b', r'\bmuseum\b', r'\barchive\b',
        r'\bpeer.review', r'\bpublished\b', r'\bjournal\b',
    ]
    return sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))

def has_aeo_opener(body):
    """First sentence has definitional verb."""
    first_para = body.split("\n\n")[0] if body else ""
    first_sent = re.split(r'[.!?]', first_para)[0] if first_para else ""
    return bool(re.search(r'\b(is|was|are|were|refers?\s+to|dates?\s+to|represents?)\b',
                          first_sent, re.IGNORECASE))

def count_question_headings(body):
    headings = re.findall(r'^##?#?\s+(.+)$', body, re.MULTILINE)
    q_words = r'^(What|When|Where|Who|Why|How|Can|Did|Does|Is|Are|Were)\b'
    return sum(1 for h in headings if re.search(q_words, h.strip(), re.IGNORECASE))

def has_definition_sentence(body):
    return bool(re.search(
        r'\b[A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*\s+(is|refers?\s+to|dates?\s+to|represents?)\s',
        body))

def has_structured_list(body):
    return bool(re.search(r'^[\-\*]\s+', body, re.MULTILINE)) or \
           bool(re.search(r'^\d+\.\s+', body, re.MULTILINE))

def has_faq_section(body):
    return bool(re.search(r'^##\s+Frequently\s+Asked\s+Questions', body, re.MULTILINE | re.IGNORECASE))

def count_evidence_hedges(text):
    patterns = [
        r'tradition\s+holds', r'scholarship\s+suggests',
        r'evidence\s+indicates', r'scholars\s+believe',
        r'according\s+to\s+tradition', r'the\s+evidence\s+suggests',
        r'historians\s+debate', r'some\s+scholars',
    ]
    return sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))

# ── Collection definitions ──────────────────────────────────────
PILGRIMAGE_COLLECTIONS = {
    "hubs":    {"min_words": 2000, "min_h2": 6, "required": ["topics"]},
    "places":  {"min_words": 1200, "min_h2": 5, "required": ["region", "country"]},
    "routes":  {"min_words": 1200, "min_h2": 5, "required": ["region", "countries"]},
    "stories": {"min_words": 1000, "min_h2": 4, "required": ["storyType"]},
    "context": {"min_words": 1000, "min_h2": 4, "required": ["contextType"]},
}

RESEARCH_CATEGORIES = ["biblical-archaeology", "scripture", "excavations", "artifacts", "faith"]

# ── Single article audit ────────────────────────────────────────
def audit_article(filepath, collection, is_research=False):
    """Audit a single article. Returns dict of results."""
    rel = filepath.relative_to(CONTENT)
    slug = filepath.stem

    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return {"slug": slug, "path": str(rel), "error": str(e), "fails": ["READ_ERROR"]}

    fm, body = parse_frontmatter(text)
    fails = []
    warnings = []
    metrics = {}

    # ── S1: Valid parse ──
    if not fm:
        fails.append("S1:no_frontmatter")

    # ── S2-S3: Title ──
    title = fm.get("title", "")
    if not title:
        fails.append("S2:no_title")
    elif len(title) > 70:
        fails.append(f"S3:title_len={len(title)}")

    # ── S4-S5: Description ──
    desc = fm.get("description", "")
    if not desc:
        fails.append("S4:no_description")
    elif len(desc) > 160:
        fails.append(f"S5:desc_len={len(desc)}")

    # ── S6: No H1 ──
    if has_h1(body):
        fails.append("S6:h1_in_body")

    # ── S7: H2 count ──
    h2_count = count_h2(body)
    min_h2 = 4
    if not is_research and collection in PILGRIMAGE_COLLECTIONS:
        min_h2 = PILGRIMAGE_COLLECTIONS[collection]["min_h2"]
    metrics["h2_count"] = h2_count
    if h2_count < min_h2:
        fails.append(f"S7:h2={h2_count}<{min_h2}")

    # ── S8: Word count ──
    wc = count_words(body)
    metrics["word_count"] = wc
    if is_research:
        tier = fm.get("siloTier", "support")
        min_wc = 1500 if tier == "pillar" else 800
    else:
        min_wc = PILGRIMAGE_COLLECTIONS.get(collection, {}).get("min_words", 1000)
    if wc < min_wc:
        fails.append(f"S8:wc={wc}<{min_wc}")

    # ── S9: Banned phrases ──
    banned_found = BANNED_RE.findall(body)
    if UNLOCK_RE.search(body):
        banned_found.append("unlock")
    if banned_found:
        fails.append(f"S9:banned={','.join(set(b.lower() for b in banned_found))}")

    # ── S10: draft ──
    if fm.get("draft", False):
        fails.append("S10:draft=true")

    # ── S11: Mojibake ──
    if MOJIBAKE_RE.search(body):
        fails.append("S11:mojibake")

    # ── Research-specific structural ──
    if is_research:
        cat = fm.get("category", "")
        if cat not in RESEARCH_CATEGORIES:
            fails.append(f"RS1:bad_category={cat}")
        for field in ["siloTier", "siloCluster", "siloParent"]:
            if not fm.get(field):
                fails.append(f"RS:{field}_missing")

    # ── Pilgrimage-specific structural ──
    if not is_research and collection in PILGRIMAGE_COLLECTIONS:
        for field in PILGRIMAGE_COLLECTIONS[collection]["required"]:
            if not fm.get(field):
                fails.append(f"STRUCT:{field}_missing")

    # ── Linking ──
    links = get_internal_links(body)
    link_count = len(links)
    metrics["internal_links"] = link_count

    if is_research:
        if link_count < 2:
            fails.append(f"RL1:links={link_count}<2")
        cat = fm.get("category", "")
        hub_path = f"/research/{cat}/"
        has_hub = any(p.rstrip("/") == hub_path.rstrip("/") for _, p in links)
        if not has_hub:
            # Also accept /research/{category} without trailing slash
            has_hub = any(f"/research/{cat}" in p for _, p in links)
        if not has_hub:
            fails.append("RL2:no_hub_link")
    else:
        if link_count < 3:
            fails.append(f"PL1:links={link_count}<3")
        parent_hub = fm.get("parentHub", "")
        if parent_hub and collection != "hubs":
            hub_path = f"/journeys/{parent_hub}/"
            has_hub = any(hub_path.rstrip("/") in p for _, p in links)
            if not has_hub:
                fails.append("PL2:no_parent_hub_link")

    # ── On-page SEO ──
    metrics["aeo_opener"] = has_aeo_opener(body)
    if not metrics["aeo_opener"]:
        fails.append("P1:no_aeo_opener")

    q_heads = count_question_headings(body)
    metrics["question_headings"] = q_heads
    if q_heads < 2:
        fails.append(f"P2:q_headings={q_heads}<2")

    metrics["has_definition"] = has_definition_sentence(body)
    if not metrics["has_definition"]:
        fails.append("P3:no_definition_sentence")

    metrics["has_list"] = has_structured_list(body)
    if not metrics["has_list"]:
        fails.append("P4:no_structured_list")

    if is_research:
        metrics["has_faq"] = has_faq_section(body)
        if not metrics["has_faq"]:
            fails.append("P5:no_faq_section")

    # ── Semantic depth ──
    entities = count_named_entities(body)
    metrics["named_entities"] = entities
    if entities < 5:
        fails.append(f"D1:entities={entities}<5")

    years = count_unique_years(body)
    metrics["unique_years"] = years
    if years < 3:
        fails.append(f"D2:years={years}<3")

    sources = count_source_refs(body)
    metrics["source_refs"] = sources
    if sources < 2:
        fails.append(f"D4:sources={sources}<2")

    h2_texts = get_h2_texts(body)
    h2_words = set()
    stop = {"the","a","an","and","or","of","in","to","for","on","at","by","with","from","is","are","was","were","its","this","that"}
    for h in h2_texts:
        for w in re.findall(r'[A-Za-z]+', h):
            if w.lower() not in stop and len(w) > 2:
                h2_words.add(w.lower())
    metrics["h2_breadth"] = len(h2_words)
    if len(h2_words) < 8:
        fails.append(f"D5:h2_breadth={len(h2_words)}<8")

    metrics["entity_density"] = round(entities / max(wc/1000, 0.1), 1)

    hedges = count_evidence_hedges(body)
    metrics["evidence_hedges"] = hedges
    if hedges < 1:
        fails.append("D8:no_evidence_hedge")

    # ── Holy Land warning ──
    if re.search(r'\bthe Holy Land\b', body) and not re.search(r'(Christian|Jewish|Muslim|Islamic)\s+Holy Land', body):
        warnings.append("WARN:unqualified_holy_land")

    return {
        "slug": slug,
        "path": str(rel),
        "collection": collection if not is_research else f"research/{fm.get('category','')}",
        "is_research": is_research,
        "fails": fails,
        "warnings": warnings,
        "metrics": metrics,
        "tier": fm.get("siloTier", "") if is_research else "",
    }

# ── Scan all articles ───────────────────────────────────────────
def scan_all(research_only=False, pilgrimage_only=False):
    results = []

    if not research_only:
        for coll in PILGRIMAGE_COLLECTIONS:
            coll_dir = CONTENT / coll
            if not coll_dir.exists():
                continue
            for f in sorted(coll_dir.glob("*.md")):
                if f.name == "homepage.md":
                    continue
                results.append(audit_article(f, coll, is_research=False))

    if not pilgrimage_only:
        research_dir = CONTENT / "research"
        if research_dir.exists():
            for f in sorted(research_dir.rglob("*.md")):
                cat = f.parent.name
                if cat == "research":
                    continue  # skip if directly in research/
                results.append(audit_article(f, cat, is_research=True))

    return results

# ── Report ──────────────────────────────────────────────────────
def print_report(results, verbose=False):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(results)
    research = [r for r in results if r.get("is_research")]
    pilgrimage = [r for r in results if not r.get("is_research")]
    perfect = [r for r in results if not r.get("fails") and not r.get("error")]
    failing = [r for r in results if r.get("fails") or r.get("error")]

    print(f"\n{'='*60}")
    print(f"  DiggingScriptures SEO Audit — {now}")
    print(f"  Spec: SEO-OPTIMIZATION-SPEC.md v1.0 | Script: audit.py v1.0")
    print(f"{'='*60}")
    print(f"\n  Total articles:    {total}")
    print(f"  Research:          {len(research)}")
    print(f"  Pilgrimage:        {len(pilgrimage)}")
    print(f"  Perfect (0 fails): {len(perfect)} ({100*len(perfect)//max(total,1)}%)")
    print(f"  Failing:           {len(failing)}")

    # ── Fail frequency ──
    fail_counter = Counter()
    for r in results:
        for f in r.get("fails", []):
            code = f.split(":")[0]
            fail_counter[code] += 1

    print(f"\n  {'─'*50}")
    print(f"  FAIL FREQUENCIES (across all articles)")
    print(f"  {'─'*50}")
    for code, count in fail_counter.most_common():
        pct = 100 * count // total
        bar = "█" * (pct // 2)
        label = "PASS" if count == 0 else f"{count}/{total} ({pct}%)"
        print(f"  {code:<25} {label:<20} {bar}")

    # ── Structural pass rates (key checks) ──
    checks = {
        "title ≤70":     lambda r: not any("S3:" in f for f in r.get("fails",[])),
        "desc ≤160":     lambda r: not any("S5:" in f for f in r.get("fails",[])),
        "H2 count":      lambda r: not any("S7:" in f for f in r.get("fails",[])),
        "word count":    lambda r: not any("S8:" in f for f in r.get("fails",[])),
        "no H1 body":    lambda r: not any("S6" in f for f in r.get("fails",[])),
        "no banned":     lambda r: not any("S9:" in f for f in r.get("fails",[])),
        "no mojibake":   lambda r: not any("S11:" in f for f in r.get("fails",[])),
        "AEO opener":    lambda r: not any("P1:" in f for f in r.get("fails",[])),
        "Q headings ≥2": lambda r: not any("P2:" in f for f in r.get("fails",[])),
        "definition":    lambda r: not any("P3:" in f for f in r.get("fails",[])),
        "has list":      lambda r: not any("P4:" in f for f in r.get("fails",[])),
        "entities ≥5":   lambda r: not any("D1:" in f for f in r.get("fails",[])),
        "years ≥3":      lambda r: not any("D2:" in f for f in r.get("fails",[])),
        "sources ≥2":    lambda r: not any("D4:" in f for f in r.get("fails",[])),
        "H2 breadth ≥8": lambda r: not any("D5:" in f for f in r.get("fails",[])),
        "hedge ≥1":      lambda r: not any("D8:" in f for f in r.get("fails",[])),
        "links (min)":   lambda r: not any(("RL1:" in f or "PL1:" in f) for f in r.get("fails",[])),
        "hub link":      lambda r: not any(("RL2:" in f or "PL2:" in f) for f in r.get("fails",[])),
    }

    print(f"\n  {'─'*50}")
    print(f"  PASS RATES BY CHECK")
    print(f"  {'─'*50}")
    for name, fn in checks.items():
        passing = sum(1 for r in results if fn(r))
        pct = 100 * passing // max(total, 1)
        print(f"  {name:<20} {passing:>4}/{total} ({pct:>3}%)")

    # ── Semantic averages ──
    metric_keys = ["named_entities", "unique_years", "source_refs", "h2_breadth", "entity_density", "evidence_hedges", "word_count"]
    print(f"\n  {'─'*50}")
    print(f"  SEMANTIC AVERAGES")
    print(f"  {'─'*50}")
    for key in metric_keys:
        vals = [r["metrics"][key] for r in results if key in r.get("metrics", {})]
        if vals:
            avg = sum(vals) / len(vals)
            print(f"  {key:<20} avg={avg:.1f}  min={min(vals)}  max={max(vals)}")

    # ── Worst articles ──
    if verbose:
        print(f"\n  {'─'*50}")
        print(f"  FAILING ARTICLES (detail)")
        print(f"  {'─'*50}")
        for r in sorted(failing, key=lambda x: -len(x.get("fails",[]))):
            n = len(r.get("fails", []))
            print(f"\n  [{n} fails] {r['path']}")
            for f in r["fails"]:
                print(f"    ✗ {f}")
    else:
        # Just top 20
        print(f"\n  {'─'*50}")
        print(f"  TOP 20 WORST ARTICLES")
        print(f"  {'─'*50}")
        for r in sorted(failing, key=lambda x: -len(x.get("fails",[])))[:20]:
            n = len(r.get("fails", []))
            print(f"  [{n:>2} fails] {r['slug']}")

    # ── Research breakdown by category ──
    if research:
        print(f"\n  {'─'*50}")
        print(f"  RESEARCH BREAKDOWN BY CATEGORY")
        print(f"  {'─'*50}")
        cats = Counter(r["collection"] for r in research)
        for cat, count in sorted(cats.items()):
            cat_results = [r for r in research if r["collection"] == cat]
            perf = sum(1 for r in cat_results if not r.get("fails"))
            print(f"  {cat:<30} {count:>4} articles  {perf:>4} perfect ({100*perf//count}%)")

    print(f"\n{'='*60}\n")

# ── Main ────────────────────────────────────────────────────────
if __name__ == "__main__":
    research_only = "--research-only" in sys.argv
    pilgrimage_only = "--pilgrimage-only" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    results = scan_all(research_only=research_only, pilgrimage_only=pilgrimage_only)
    print_report(results, verbose=verbose)
