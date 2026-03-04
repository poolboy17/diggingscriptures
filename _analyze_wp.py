"""Analyze WP posts - compact summary of published posts."""
import json

with open(r"D:\dev\projects\diggingscriptures\_wp_posts.json", "r", encoding="utf-8") as f:
    data = json.load(f)

pub = data['published']
drafts = data['drafts']

print(f"PUBLISHED POSTS: {len(pub)}")
print(f"DRAFT POSTS: {len(drafts)}")
print()

# Google-indexed URLs from our earlier search
indexed_slugs = [
    'how-many-times-has-the-bible-been-changed',
    'continuity-and-discontinuity-the-relationship-between-the-old-testament-and-the-new-testament',
    'were-the-new-testament-books-written-in-hebrew',
    'the-ultimate-beginners-guide-to-biblical-archaeology',
    'is-the-ethiopian-bible-the-most-accurate',
    'what-is-the-difference-between-the-ethiopian-bible-and-the-bible',
]

print("=" * 90)
print(f"{'#':<3} {'Words':<6} {'IDX':<4} {'Slug':<60} {'Title'}")
print("=" * 90)

for i, p in enumerate(pub, 1):
    cats = [c['label'] for c in p['categories'] if c['domain'] == 'category']
    cat_str = ', '.join(cats)
    idx = "YES" if p['slug'] in indexed_slugs else ""
    print(f"{i:<3} {p['word_count']:<6} {idx:<4} {p['slug'][:60]:<60} {p['title'][:50]}")

print()
print("=" * 90)
print("CATEGORY BREAKDOWN")
print("=" * 90)

cat_counts = {}
for p in pub:
    for c in p['categories']:
        if c['domain'] == 'category':
            cat_counts[c['label']] = cat_counts.get(c['label'], 0) + 1

for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
    print(f"  {count:>3}x  {cat}")

print()
print("=" * 90)
print("WORD COUNT STATS")
print("=" * 90)

wcs = [p['word_count'] for p in pub]
print(f"  Total posts: {len(wcs)}")
print(f"  Total words: {sum(wcs):,}")
print(f"  Avg words:   {sum(wcs)//len(wcs):,}")
print(f"  Min words:   {min(wcs):,}")
print(f"  Max words:   {max(wcs):,}")
print(f"  >3000 words: {len([w for w in wcs if w > 3000])}")
print(f"  >1000 words: {len([w for w in wcs if w > 1000])}")
print(f"  <500 words:  {len([w for w in wcs if w < 500])}")

# Pilgrimage-relevant keywords
pilgrimage_kw = ['pilgrim', 'jerusalem', 'temple', 'holy land', 'sacred',
    'mecca', 'hajj', 'crusade', 'holy city', 'shrine', 'relic',
    'camino', 'pilgrimage', 'holy site', 'biblical site', 'exodus',
    'promised land', 'covenant', 'tabernacle', 'ark']

print()
print("=" * 90)
print("PILGRIMAGE-ADJACENT CONTENT (keyword matches in title/preview)")
print("=" * 90)

for i, p in enumerate(pub, 1):
    text = (p['title'] + ' ' + p['content_preview']).lower()
    matches = [kw for kw in pilgrimage_kw if kw in text]
    if matches:
        print(f"\n  {p['title'][:70]}")
        print(f"  Slug: {p['slug']}")
        print(f"  Words: {p['word_count']}  Keywords: {', '.join(matches)}")

print()
print("=" * 90)
print("DRAFTS (may have usable content)")
print("=" * 90)

for i, p in enumerate(drafts, 1):
    if p['word_count'] > 100:
        cats = [c['label'] for c in p['categories'] if c['domain'] == 'category']
        print(f"\n  {p['title'][:70]}")
        print(f"  Slug: {p['slug']}  Words: {p['word_count']}")
        print(f"  Categories: {', '.join(cats)}")
