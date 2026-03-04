"""
Curation pipeline for WordPress posts.
Scores each post on: word count, uniqueness, category fit, slug quality.
Flags duplicates. Outputs ranked list of keepers.
"""
import re
import html
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from difflib import SequenceMatcher

XML_PATH = r"D:\New folder\diggingscriptures.xml"
NS = {
    'wp': 'http://wordpress.org/export/1.2/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
}

# Silo mapping — which WP categories map to which spoke
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

# Google-indexed slugs — auto-keep
INDEXED_SLUGS = {
    'the-ultimate-beginners-guide-to-biblical-archaeology',
    'were-the-new-testament-books-written-in-hebrew',
    'continuity-and-discontinuity-the-relationship-between-the-old-testament-and-the-new-testament',
    'is-the-ethiopian-bible-the-most-accurate',
    'what-is-the-difference-between-the-ethiopian-bible-and-the-bible',
    'how-many-times-has-the-bible-been-changed',
}

def strip_html(text):
    """Strip HTML tags, decode entities."""
    text = re.sub(r'</(p|h[1-6]|li|div|blockquote)>', '\n\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text

def get_h2s(html_content):
    """Extract H2 headings from HTML."""
    return re.findall(r'<h2[^>]*>(.*?)</h2>', html_content, re.IGNORECASE | re.DOTALL)

def title_similarity(t1, t2):
    """Ratio of title similarity (0-1)."""
    return SequenceMatcher(None, t1.lower(), t2.lower()).ratio()

def compute_quality_score(post, all_titles):
    """Score a post 0-100 based on multiple quality signals."""
    score = 0
    wc = post['word_count']
    
    # Word count score (0-30)
    if wc >= 3000: score += 30
    elif wc >= 2000: score += 25
    elif wc >= 1500: score += 20
    elif wc >= 1000: score += 15
    elif wc >= 800: score += 8
    else: score += 0  # Under 800 = very low
    
    # H2 structure (0-15) — well-structured articles have many H2s
    h2_count = len(post.get('h2s', []))
    if h2_count >= 8: score += 15
    elif h2_count >= 5: score += 12
    elif h2_count >= 3: score += 8
    elif h2_count >= 1: score += 4
    
    # Slug quality (0-10) — specific > generic
    slug = post['slug']
    generic_prefixes = ['exploring-', 'unveiling-', 'unearthing-', 'discovering-',
                        'uncovering-', 'unraveling-', 'deciphering-', 'unlocking-']
    if any(slug.startswith(p) for p in generic_prefixes):
        score += 2  # Generic slug
    elif len(slug) < 60:
        score += 10  # Clean specific slug
    else:
        score += 5
    
    # Uniqueness (0-20) — penalize near-duplicate titles
    title = post['title'].lower()
    similar_count = sum(1 for t in all_titles 
                        if t != post['title'] and title_similarity(title, t.lower()) > 0.85)
    if similar_count == 0: score += 20
    elif similar_count == 1: score += 10
    else: score += 0  # Multiple near-dupes
    
    # Google indexed bonus (0-15)
    if slug in INDEXED_SLUGS:
        score += 15
    
    # Category fit (0-10) — posts with clear silo assignment
    cats = [c['label'] for c in post['categories'] if c['domain'] == 'category']
    silo_hits = sum(1 for c in cats if c in SILO_MAP)
    if silo_hits >= 2: score += 10
    elif silo_hits == 1: score += 7
    else: score += 2
    
    return score

def assign_silo(post):
    """Assign post to best-fit silo based on categories."""
    cats = [c['label'] for c in post['categories'] if c['domain'] == 'category']
    silo_votes = Counter()
    for c in cats:
        if c in SILO_MAP:
            silo_votes[SILO_MAP[c]] += 1
    if silo_votes:
        return silo_votes.most_common(1)[0][0]
    return 'history'  # Default fallback

# ============================================================
# MAIN
# ============================================================
print("Loading WordPress XML (41MB)...")
with open(XML_PATH, "r", encoding="utf-8", errors="replace") as f:
    raw = f.read()
raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)

print("Parsing XML...")
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

    title_el = item.find('title')
    title = title_el.text if title_el is not None and title_el.text else ''
    slug_el = item.find('wp:post_name', NS)
    slug = slug_el.text if slug_el is not None and slug_el.text else ''
    ce = item.find('content:encoded', NS)
    content_html = ce.text if ce is not None and ce.text else ''
    ee = item.find('excerpt:encoded', NS)
    excerpt = ee.text if ee is not None and ee.text else ''
    pd = item.find('pubDate')
    pub_date = pd.text if pd is not None and pd.text else ''

    cats = []
    for cat in item.findall('category'):
        domain = cat.get('domain', '')
        nicename = cat.get('nicename', '')
        label = cat.text or ''
        cats.append({'domain': domain, 'nicename': nicename, 'label': label})

    plain = strip_html(content_html)
    wc = len(plain.split())
    h2s = get_h2s(content_html)

    posts.append({
        'title': title, 'slug': slug, 'content_html': content_html,
        'plain_text': plain, 'excerpt': excerpt, 'pub_date': pub_date,
        'word_count': wc, 'h2s': h2s, 'categories': cats,
    })

print(f"Loaded {len(posts)} published posts")

# Score all posts
all_titles = [p['title'] for p in posts]
for p in posts:
    p['quality_score'] = compute_quality_score(p, all_titles)
    p['silo'] = assign_silo(p)

# Sort by quality score descending
posts.sort(key=lambda x: x['quality_score'], reverse=True)

# Find duplicate clusters (titles >85% similar)
seen_titles = {}
for p in posts:
    title_lower = p['title'].lower().strip()
    is_dupe = False
    for seen_t, seen_slug in seen_titles.items():
        if title_similarity(title_lower, seen_t) > 0.85:
            p['dupe_of'] = seen_slug
            is_dupe = True
            break
    if not is_dupe:
        seen_titles[title_lower] = p['slug']
        p['dupe_of'] = None

# Classify posts
keepers = [p for p in posts if p['dupe_of'] is None and p['word_count'] >= 800]
dupes = [p for p in posts if p['dupe_of'] is not None]
thin = [p for p in posts if p['dupe_of'] is None and p['word_count'] < 800]

# Stats
print(f"\nCURATION RESULTS:")
print(f"  Keepers (unique, >=800w): {len(keepers)}")
print(f"  Duplicates (dropped):     {len(dupes)}")
print(f"  Thin (<800w, dropped):    {len(thin)}")

# Silo breakdown of keepers
silo_counts = Counter(p['silo'] for p in keepers)
print(f"\nSILO BREAKDOWN (keepers):")
for silo, count in silo_counts.most_common():
    avg_wc = sum(p['word_count'] for p in keepers if p['silo'] == silo) // count
    print(f"  {silo:>12}: {count:>4} posts  (avg {avg_wc}w)")

# Quality score distribution
print(f"\nQUALITY SCORE DISTRIBUTION (keepers):")
q_buckets = {'80-100': 0, '60-79': 0, '40-59': 0, '20-39': 0, '0-19': 0}
for p in keepers:
    s = p['quality_score']
    if s >= 80: q_buckets['80-100'] += 1
    elif s >= 60: q_buckets['60-79'] += 1
    elif s >= 40: q_buckets['40-59'] += 1
    elif s >= 20: q_buckets['20-39'] += 1
    else: q_buckets['0-19'] += 1

for bucket, count in q_buckets.items():
    bar = '#' * (count // 3)
    print(f"  {bucket}: {count:>4}  {bar}")

# Top 30 keepers
print(f"\nTOP 30 KEEPERS BY QUALITY SCORE:")
print(f"{'Score':>5} {'Words':>5} {'Silo':>12} {'Slug'}")
print("-" * 90)
for p in keepers[:30]:
    print(f"{p['quality_score']:>5} {p['word_count']:>5} {p['silo']:>12} {p['slug'][:60]}")

# Bottom 10 keepers (borderline)
print(f"\nBOTTOM 10 KEEPERS (borderline):")
for p in keepers[-10:]:
    print(f"{p['quality_score']:>5} {p['word_count']:>5} {p['silo']:>12} {p['slug'][:60]}")

# Save keepers list as JSON (without full content — just metadata)
keepers_meta = []
for p in keepers:
    keepers_meta.append({
        'title': p['title'],
        'slug': p['slug'],
        'word_count': p['word_count'],
        'quality_score': p['quality_score'],
        'silo': p['silo'],
        'h2_count': len(p['h2s']),
        'indexed': p['slug'] in INDEXED_SLUGS,
        'categories': [c['label'] for c in p['categories'] if c['domain'] == 'category'],
        'excerpt': (p['excerpt'] or p['plain_text'][:200])[:200],
    })

with open(r"D:\dev\projects\diggingscriptures\_keepers.json", "w", encoding="utf-8") as f:
    json.dump(keepers_meta, f, indent=2, ensure_ascii=False)

# Also save full keepers with content for the converter
keepers_full = []
for p in keepers:
    keepers_full.append({
        'title': p['title'],
        'slug': p['slug'],
        'word_count': p['word_count'],
        'quality_score': p['quality_score'],
        'silo': p['silo'],
        'h2s': [strip_html(h) for h in p['h2s']],
        'indexed': p['slug'] in INDEXED_SLUGS,
        'categories': [c['label'] for c in p['categories'] if c['domain'] == 'category'],
        'excerpt': (p['excerpt'] or p['plain_text'][:200])[:200],
        'content_html': p['content_html'],
        'pub_date': p['pub_date'],
    })

with open(r"D:\dev\projects\diggingscriptures\_keepers_full.json", "w", encoding="utf-8") as f:
    json.dump(keepers_full, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(keepers_meta)} keepers to _keepers.json")
print(f"Saved {len(keepers_full)} keepers (with content) to _keepers_full.json")
