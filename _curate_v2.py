"""
Curation pipeline v2 — faster dedup using normalized title hashing.
"""
import re
import html
import json
import xml.etree.ElementTree as ET
from collections import Counter

XML_PATH = r"D:\New folder\diggingscriptures.xml"
NS = {
    'wp': 'http://wordpress.org/export/1.2/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
}

SILO_MAP = {
    'Sacred Sites & Places': 'sites',
    'Ancient Objects & Relics': 'artifacts',
    'Excavation Findings': 'artifacts',
    'Archaeological Discoveries': 'discoveries',
    'Recent Excavations': 'discoveries',
    'Scriptural Analysis': 'scripture',
    'Ancient Texts & Scrolls': 'scripture',
    'Text Origins & Manuscript Studies': 'scripture',
    'Bible Origins & Manuscript Studies': 'scripture',
    'Language & Linguistics': 'scripture',
    'Ancient Near East History': 'history',
    'Ancient Civilizations': 'history',
    'Ancient History': 'history',
    'Historical Narratives': 'history',
    'Worship & Rituals': 'faith',
    'Theological Studies': 'faith',
    'Faith & Theology': 'faith',
    'Prominent Researchers': 'methods',
    'Technology & Modern Life': 'methods',
}

INDEXED_SLUGS = {
    'the-ultimate-beginners-guide-to-biblical-archaeology',
    'were-the-new-testament-books-written-in-hebrew',
    'continuity-and-discontinuity-the-relationship-between-the-old-testament-and-the-new-testament',
    'is-the-ethiopian-bible-the-most-accurate',
    'what-is-the-difference-between-the-ethiopian-bible-and-the-bible',
    'how-many-times-has-the-bible-been-changed',
}

def strip_html(text):
    text = re.sub(r'</(p|h[1-6]|li|div|blockquote)>', '\n\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()

def normalize_title(t):
    """Normalize title for dedup — lowercase, remove punctuation, strip numbers."""
    t = t.lower().strip()
    t = re.sub(r'[^a-z\s]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    # Remove trailing numbers (like "-2", "-3", "-4" variants)
    return t

def assign_silo(cats):
    silo_votes = Counter()
    for c in cats:
        if c in SILO_MAP:
            silo_votes[SILO_MAP[c]] += 1
    return silo_votes.most_common(1)[0][0] if silo_votes else 'history'

def get_h2s(html_content):
    return re.findall(r'<h2[^>]*>(.*?)</h2>', html_content, re.IGNORECASE | re.DOTALL)

# ============================================================
print("Loading WordPress XML...")
with open(XML_PATH, "r", encoding="utf-8", errors="replace") as f:
    raw = f.read()
raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)

print("Parsing...")
root = ET.fromstring(raw)
channel = root.find('channel')

posts = []
for item in channel.findall('item'):
    pt = item.find('wp:post_type', NS)
    if pt is None or pt.text != 'post':
        continue
    st = item.find('wp:status', NS)
    if st is None or st.text != 'publish':
        continue
    title = (item.find('title').text or '').strip()
    slug = (item.find('wp:post_name', NS).text or '').strip()
    ce = item.find('content:encoded', NS)
    content_html = ce.text if ce is not None and ce.text else ''
    ee = item.find('excerpt:encoded', NS)
    excerpt = ee.text if ee is not None and ee.text else ''
    pd_el = item.find('pubDate')
    pub_date = pd_el.text if pd_el is not None and pd_el.text else ''

    cats = [c.text for c in item.findall('category') 
            if c.get('domain') == 'category' and c.text]

    plain = strip_html(content_html)
    wc = len(plain.split())
    h2s = get_h2s(content_html)
    silo = assign_silo(cats)

    posts.append({
        'title': title, 'slug': slug, 'word_count': wc,
        'h2_count': len(h2s), 'silo': silo, 'categories': cats,
        'excerpt': (excerpt or plain[:200])[:200],
        'pub_date': pub_date,
        'content_html': content_html, 'plain_text': plain,
        'h2s': [strip_html(h) for h in h2s],
        'indexed': slug in INDEXED_SLUGS,
    })

print(f"Loaded {len(posts)} published posts")

# ============================================================
# DEDUP — fast approach using normalized title keys
# ============================================================
# Sort by word count DESC so we keep the longest version of dupes
posts.sort(key=lambda x: x['word_count'], reverse=True)

seen_norm = {}  # normalized_title -> slug of keeper
for p in posts:
    norm = normalize_title(p['title'])
    if norm in seen_norm:
        p['dupe_of'] = seen_norm[norm]
    else:
        seen_norm[norm] = p['slug']
        p['dupe_of'] = None

# Also check slug-based dupes (same slug with -2, -3 suffix)
base_slugs = {}
for p in posts:
    if p['dupe_of'] is not None:
        continue
    base = re.sub(r'-\d+$', '', p['slug'])
    if base in base_slugs and base != p['slug']:
        # Keep the one with higher word count (already sorted)
        p['dupe_of'] = base_slugs[base]
    else:
        base_slugs[base] = p['slug']

# ============================================================
# SCORING
# ============================================================
for p in posts:
    score = 0
    wc = p['word_count']
    # Word count (0-30)
    if wc >= 3000: score += 30
    elif wc >= 2000: score += 25
    elif wc >= 1500: score += 20
    elif wc >= 1000: score += 15
    elif wc >= 800: score += 8
    # H2 structure (0-15)
    h2c = p['h2_count']
    if h2c >= 8: score += 15
    elif h2c >= 5: score += 12
    elif h2c >= 3: score += 8
    elif h2c >= 1: score += 4

    # Slug quality (0-10)
    slug = p['slug']
    generic = ['exploring-', 'unveiling-', 'unearthing-', 'discovering-',
               'uncovering-', 'unraveling-', 'deciphering-', 'unlocking-']
    if any(slug.startswith(g) for g in generic):
        score += 2
    elif len(slug) < 60:
        score += 10
    else:
        score += 5

    # Uniqueness (0-20) — no dupe = full score
    if p['dupe_of'] is None:
        score += 20

    # Google indexed (0-15)
    if p['indexed']:
        score += 15

    # Category fit (0-10)
    silo_hits = sum(1 for c in p['categories'] if c in SILO_MAP)
    if silo_hits >= 2: score += 10
    elif silo_hits == 1: score += 7
    else: score += 2

    p['quality_score'] = score

# ============================================================
# CLASSIFY
# ============================================================
keepers = [p for p in posts if p['dupe_of'] is None and p['word_count'] >= 800]
dupes = [p for p in posts if p['dupe_of'] is not None]
thin = [p for p in posts if p['dupe_of'] is None and p['word_count'] < 800]

keepers.sort(key=lambda x: x['quality_score'], reverse=True)

print(f"\nCURATION RESULTS:")
print(f"  Keepers (unique, >=800w): {len(keepers)}")
print(f"  Duplicates (dropped):     {len(dupes)}")
print(f"  Thin (<800w, dropped):    {len(thin)}")

silo_counts = Counter(p['silo'] for p in keepers)
print(f"\nSILO BREAKDOWN (keepers):")
for silo, count in silo_counts.most_common():
    avg_wc = sum(p['word_count'] for p in keepers if p['silo'] == silo) // count
    print(f"  {silo:>12}: {count:>4} posts  (avg {avg_wc}w)")

print(f"\nQUALITY SCORE DISTRIBUTION (keepers):")
for lo, hi, label in [(80,101,'80-100'),(60,80,'60-79'),(40,60,'40-59'),(20,40,'20-39'),(0,20,'0-19')]:
    c = len([p for p in keepers if lo <= p['quality_score'] < hi])
    bar = '#' * (c // 3)
    print(f"  {label}: {c:>4}  {bar}")

print(f"\nTOP 30 KEEPERS:")
print(f"{'Sc':>3} {'Wds':>5} {'H2s':>3} {'Silo':>12} {'Slug'}")
print("-" * 90)
for p in keepers[:30]:
    idx = "*" if p['indexed'] else " "
    print(f"{p['quality_score']:>3} {p['word_count']:>5} {p['h2_count']:>3} {p['silo']:>12} {idx}{p['slug'][:58]}")

print(f"\nBOTTOM 10 KEEPERS (borderline):")
for p in keepers[-10:]:
    print(f"{p['quality_score']:>3} {p['word_count']:>5} {p['h2_count']:>3} {p['silo']:>12} {p['slug'][:58]}")

# Save keepers metadata
meta = [{
    'title': p['title'], 'slug': p['slug'], 'word_count': p['word_count'],
    'quality_score': p['quality_score'], 'silo': p['silo'],
    'h2_count': p['h2_count'], 'indexed': p['indexed'],
    'categories': p['categories'], 'excerpt': p['excerpt'],
} for p in keepers]

with open(r"D:\dev\projects\diggingscriptures\_keepers.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)

# Save full content for converter
full = [{
    'title': p['title'], 'slug': p['slug'], 'word_count': p['word_count'],
    'quality_score': p['quality_score'], 'silo': p['silo'],
    'h2s': p['h2s'], 'indexed': p['indexed'],
    'categories': p['categories'], 'excerpt': p['excerpt'],
    'content_html': p['content_html'], 'pub_date': p['pub_date'],
} for p in keepers]

with open(r"D:\dev\projects\diggingscriptures\_keepers_full.json", "w", encoding="utf-8") as f:
    json.dump(full, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(meta)} keepers to _keepers.json")
print(f"Saved {len(full)} keepers (with content) to _keepers_full.json")
