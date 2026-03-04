"""Parse WordPress XML export - sanitize invalid chars first."""
import re
import html
import json
import xml.etree.ElementTree as ET

XML_PATH = r"D:\New folder\diggingscriptures.xml"

NS = {
    'wp': 'http://wordpress.org/export/1.2/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
    'dc': 'http://purl.org/dc/elements/1.1/',
}

# Read raw and strip invalid XML characters
print("Reading XML file...")
with open(XML_PATH, "r", encoding="utf-8", errors="replace") as f:
    raw = f.read()

print(f"Raw size: {len(raw):,} chars")
# Remove XML-illegal control characters
raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)

print("Parsing XML...")
root = ET.fromstring(raw)
channel = root.find('channel')

posts = []
for item in channel.findall('item'):
    pt = item.find('wp:post_type', NS)
    if pt is None:
        continue
    pt = pt.text

    st = item.find('wp:status', NS)
    st = st.text if st is not None else 'unknown'

    t = item.find('title')
    title = t.text if t is not None and t.text else '(no title)'

    lnk = item.find('link')
    link = lnk.text if lnk is not None and lnk.text else ''

    sl = item.find('wp:post_name', NS)
    slug = sl.text if sl is not None and sl.text else ''

    ce = item.find('content:encoded', NS)
    content = ce.text if ce is not None and ce.text else ''

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

    # Word count
    plain = re.sub(r'<[^>]+>', '', content)
    plain = html.unescape(plain)
    wc = len(plain.split())

    posts.append({
        'type': pt, 'status': st, 'title': title, 'slug': slug,
        'link': link, 'pub_date': pub_date, 'excerpt': excerpt[:200],
        'word_count': wc, 'categories': cats,
        'content_preview': plain[:300],
    })

print(f"Total items: {len(posts)}\n")

by_type = {}
for p in posts:
    by_type.setdefault(p['type'], []).append(p)
for t, items in sorted(by_type.items()):
    pub = len([i for i in items if i['status'] == 'publish'])
    dft = len([i for i in items if i['status'] == 'draft'])
    oth = len(items) - pub - dft
    print(f"  {t}: {len(items)} total ({pub} published, {dft} drafts, {oth} other)")

print("\n" + "=" * 80)
print("PUBLISHED POSTS (sorted by word count)")
print("=" * 80)

pub_posts = sorted(
    [p for p in posts if p['type'] == 'post' and p['status'] == 'publish'],
    key=lambda x: x['word_count'], reverse=True
)

for i, p in enumerate(pub_posts, 1):
    cats_str = ', '.join([c['label'] for c in p['categories'] if c['domain'] == 'category'])
    print(f"\n{i}. {p['title']}")
    print(f"   Slug: {p['slug']}")
    print(f"   URL:  {p['link']}")
    print(f"   Words: {p['word_count']}")
    print(f"   Date: {p['pub_date']}")
    print(f"   Categories: {cats_str}")

# Also show drafts
print("\n" + "=" * 80)
print("DRAFT POSTS")
print("=" * 80)

drafts = sorted(
    [p for p in posts if p['type'] == 'post' and p['status'] == 'draft'],
    key=lambda x: x['word_count'], reverse=True
)

for i, p in enumerate(drafts, 1):
    cats_str = ', '.join([c['label'] for c in p['categories'] if c['domain'] == 'category'])
    print(f"\n{i}. {p['title']}")
    print(f"   Slug: {p['slug']}")
    print(f"   Words: {p['word_count']}")
    print(f"   Categories: {cats_str}")

# Save JSON
with open(r"D:\dev\projects\diggingscriptures\_wp_posts.json", "w", encoding="utf-8") as f:
    json.dump({'published': pub_posts, 'drafts': drafts}, f, indent=2, ensure_ascii=False)
print(f"\nSaved to _wp_posts.json")
