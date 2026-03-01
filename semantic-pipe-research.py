#!/usr/bin/env python3
"""
SemanticPipe — Research Edition
Optimizes title, description, banned phrases, and computes semantic scores
for the 698 /research/ articles (biblical archaeology content).

Usage:
  python semantic-pipe-research.py --all --force         # Optimize all
  python semantic-pipe-research.py --all --diff          # Preview changes
  python semantic-pipe-research.py --chunk 0 --chunks 4  # Process chunk 0 of 4
"""

import os, sys, re, json, copy, argparse, threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SPEC_VERSION = "DiggingScriptures-Research-1.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESEARCH_DIR = os.path.join(BASE_DIR, "src", "content", "research")
AUDIT_LOG = os.path.join(BASE_DIR, "SEMANTIC-AUDIT-RESEARCH.md")
AUDIT_JSON = os.path.join(BASE_DIR, "semantic-audit-research.jsonl")
audit_lock = threading.Lock()

CATEGORIES = ["biblical-archaeology", "scripture", "excavations", "artifacts", "faith"]

# Archaeology / biblical studies keywords (replaces pilgrimage keywords)
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


# ── YAML Frontmatter Parser (same as original) ──────────────
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


# ── Title Optimizer (archaeology-tuned) ─────────────────────
def has_topic_keyword(title):
    t = title.lower()
    return any(kw in t for kw in TOPIC_KEYWORDS)

def optimize_title(title, category):
    changes = []
    original = title
    # Fix title casing: "BeginnerS" -> "Beginner's", etc
    title = re.sub(r'(\w)S\b', r"\1's", title)  # Fix possessive S artifacts
    # Already good?
    if 30 <= len(title) <= 65 and has_topic_keyword(title):
        if title != original:
            changes.append(f"Title fix: '{original[:40]}' -> '{title[:40]}'")
        return title, changes
    # Too long — trim at word boundary
    if len(title) > 65:
        truncated = title[:65]
        last_space = truncated.rfind(' ')
        if last_space > 30:
            title = truncated[:last_space]
        else:
            title = truncated[:64]
    # Too short — enrich with category suffix
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
    # Too long
    if len(desc) > 155:
        t = desc[:155]
        lp = t.rfind('.')
        if lp > 100:
            desc = t[:lp+1]
        else:
            ls = t.rfind(' ')
            desc = t[:ls].rstrip(',;:') + '.' if ls > 100 else t[:154] + '.'
    # Too short — enrich from body
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
    # Still short — pad with category-specific text
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

# ── Semantic Score Computer ─────────────────────────────────
def compute_scores(body, plain, wc):
    entities = set()
    for m in re.finditer(r'\b([A-Z][a-z]+(?:\s+(?:of|the|and))?(?:\s+[A-Z][a-z]+)+)\b', plain):
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


# ── Inventory Loader (nested research folders) ──────────────
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

# ── Core Optimizer ──────────────────────────────────────────
def optimize_article(slug, data, dry_run=False, show_diff=False):
    filepath = data['filepath']
    category = data['category']
    fm = copy.deepcopy(data['fm'])
    body = data['body']
    changes = []
    orig_title = fm.get('title', '')
    orig_desc = fm.get('description', '')

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

    # 4. Semantic scores
    plain = strip_markdown(body)
    wc = count_words(body)
    scores = compute_scores(body, plain, wc)

    result = {
        'slug': slug, 'category': category,
        'changes': changes, 'scores': scores,
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

    if dry_run:
        result['status'] = 'DRY_RUN'
        return result

    # Save
    save_frontmatter(filepath, fm)
    # If banned phrases were fixed, rewrite body too
    if any('Removed' in c for c in changes):
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
             'title_len': result['title_len'], 'desc_len': result['desc_len'],
             'word_count': wc}
    with audit_lock:
        with open(AUDIT_JSON, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return result


# ── Pipeline Runner ─────────────────────────────────────────
def run_pipeline(slugs, articles, threads=4, dry_run=False, show_diff=False):
    print(f"\n{'='*70}")
    print(f"SemanticPipe — Research Edition")
    print(f"Articles: {len(slugs)} | Threads: {threads} | Dry run: {dry_run}")
    print(f"{'='*70}\n")

    saved, errors = [], []
    start = datetime.now()

    def process(slug):
        try:
            return optimize_article(slug, articles[slug], dry_run, show_diff)
        except Exception as e:
            return {'slug': slug, 'status': 'ERROR', 'error': str(e), 'changes': []}

    with ThreadPoolExecutor(max_workers=threads) as ex:
        futures = {ex.submit(process, s): s for s in slugs}
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            s = r['slug']
            st = r['status']
            nc = len(r.get('changes', []))
            if st == 'ERROR':
                errors.append(r)
                print(f"  [{i:3d}/{len(slugs)}] ERR   {s[:50]:50s} {r.get('error','')[:30]}")
            else:
                saved.append(r)
                detail = f"{nc}chg t={r.get('title_len',0)}c d={r.get('desc_len',0)}c {r.get('word_count',0)}w"
                print(f"  [{i:3d}/{len(slugs)}] {'DRY' if dry_run else 'OK':5s} {s[:50]:50s} {detail}")
                if show_diff and r.get('diff'):
                    for d in r['diff']:
                        print(f"         {d}")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n{'='*70}")
    print(f"DONE in {elapsed:.1f}s ({elapsed/max(len(slugs),1):.3f}s/article)")
    print(f"  Saved: {len(saved)} | Errors: {len(errors)}")

    # Stats
    changed = [r for r in saved if r.get('changes')]
    short_t = [r for r in saved if r.get('title_len', 0) < 30]
    long_t = [r for r in saved if r.get('title_len', 0) > 65]
    short_d = [r for r in saved if r.get('desc_len', 0) < 120]
    long_d = [r for r in saved if r.get('desc_len', 0) > 155]

    print(f"  Articles changed: {len(changed)}")
    if short_t: print(f"  Short titles (<30c): {len(short_t)}")
    if long_t: print(f"  Long titles (>65c): {len(long_t)}")
    if short_d: print(f"  Short descs (<120c): {len(short_d)}")
    if long_d: print(f"  Long descs (>155c): {len(long_d)}")

    if saved:
        avg_e = sum(r['scores']['entities'] for r in saved) / len(saved)
        avg_y = sum(r['scores']['years'] for r in saved) / len(saved)
        avg_p = sum(r['scores']['namedPeople'] for r in saved) / len(saved)
        avg_s = sum(r['scores']['sourceRefs'] for r in saved) / len(saved)
        print(f"\n  Avg Semantic: entities={avg_e:.1f} years={avg_y:.1f} people={avg_p:.1f} sources={avg_s:.1f}")

    # Category breakdown
    print(f"\n  By Category:")
    for cat in CATEGORIES:
        cat_arts = [r for r in saved if r.get('category') == cat]
        if cat_arts:
            avg_wc = sum(r.get('word_count',0) for r in cat_arts) / len(cat_arts)
            chg = sum(1 for r in cat_arts if r.get('changes'))
            print(f"    {cat:25s} {len(cat_arts):3d} articles  avg {avg_wc:.0f}w  {chg} changed")

    print(f"{'='*70}")
    if errors:
        print(f"\nErrors:")
        for r in errors:
            print(f"  {r['slug']}: {r.get('error','')}")
    return {'saved': len(saved), 'errors': len(errors), 'elapsed': elapsed}


# ── CLI Entry Point ─────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='SemanticPipe — Research Edition')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
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
    elif args.all or args.force:
        slugs = sorted(articles.keys())
    else:
        print("Use --all, --force, or --category")
        sys.exit(0)

    # Chunking support for parallel runs
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

    run_pipeline(slugs, articles, threads=args.threads, dry_run=args.dry_run, show_diff=args.diff)

if __name__ == '__main__':
    main()
