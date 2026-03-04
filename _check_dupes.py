"""Check for duplicate/near-duplicate titles and content overlap."""
import json
from collections import Counter

with open(r"D:\dev\projects\diggingscriptures\_wp_posts.json", "r", encoding="utf-8") as f:
    data = json.load(f)

pub = data['published']

# 1. Exact duplicate titles
titles = [p['title'] for p in pub]
title_counts = Counter(titles)
dupes = {t: c for t, c in title_counts.items() if c > 1}

print("=" * 80)
print(f"EXACT DUPLICATE TITLES: {len(dupes)}")
print("=" * 80)
for t, c in sorted(dupes.items(), key=lambda x: -x[1]):
    print(f"  {c}x  {t}")
    for p in pub:
        if p['title'] == t:
            print(f"       -> {p['slug']} ({p['word_count']}w)")

# 2. Category distribution (how many per category)
print()
print("=" * 80)
print("POSTS PER CATEGORY (for silo planning)")
print("=" * 80)
cat_posts = {}
for p in pub:
    for c in p['categories']:
        if c['domain'] == 'category':
            cat_posts.setdefault(c['label'], []).append(p)

for cat, posts in sorted(cat_posts.items(), key=lambda x: -len(x[1])):
    wcs = [p['word_count'] for p in posts]
    print(f"  {len(posts):>4}  {cat}")
    print(f"        Avg: {sum(wcs)//len(wcs)}w  Min: {min(wcs)}w  Max: {max(wcs)}w")

# 3. Word count distribution
print()
print("=" * 80)
print("WORD COUNT BUCKETS")
print("=" * 80)
buckets = {
    '5000+': 0, '3000-5000': 0, '2000-3000': 0,
    '1500-2000': 0, '1000-1500': 0, '500-1000': 0, '<500': 0
}
for p in pub:
    w = p['word_count']
    if w >= 5000: buckets['5000+'] += 1
    elif w >= 3000: buckets['3000-5000'] += 1
    elif w >= 2000: buckets['2000-3000'] += 1
    elif w >= 1500: buckets['1500-2000'] += 1
    elif w >= 1000: buckets['1000-1500'] += 1
    elif w >= 500: buckets['500-1000'] += 1
    else: buckets['<500'] += 1

for bucket, count in buckets.items():
    bar = '#' * (count // 5)
    print(f"  {bucket:>10}: {count:>4}  {bar}")

# 4. How many have "ark" in content_preview (Ark spam check)
ark_posts = [p for p in pub if 'ark' in p['content_preview'].lower()
             or 'ark of the covenant' in p['title'].lower()]
print(f"\nPosts mentioning 'Ark' in preview or title: {len(ark_posts)}")

# 5. Posts with unique/non-generic slugs (quality signal)
generic_prefixes = ['exploring-', 'unveiling-', 'unearthing-', 'discovering-',
                    'uncovering-', 'unraveling-', 'deciphering-', 'unlocking-']
generic_count = sum(1 for p in pub 
                    if any(p['slug'].startswith(pf) for pf in generic_prefixes))
print(f"Posts with generic 'Exploring/Unveiling/Unearthing' slug prefix: {generic_count}")
print(f"Posts with specific slugs: {len(pub) - generic_count}")
