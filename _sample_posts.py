"""Sample a mix of posts to assess content quality."""
import json
import re
import html

with open(r"D:\dev\projects\diggingscriptures\_wp_posts.json", "r", encoding="utf-8") as f:
    data = json.load(f)

pub = data['published']

# Pick samples: top by word count, a few indexed ones, a few mid-range
samples = []
slugs_wanted = [
    # Indexed by Google
    'the-ultimate-beginners-guide-to-biblical-archaeology',
    'how-many-times-has-the-bible-been-changed',
    'were-the-new-testament-books-written-in-hebrew',
    # Pilgrimage-adjacent
    'exploring-ancient-jerusalem-pilgrim-routes-unearthed',
    'ancient-jerusalem-street-reveals-temple-pilgrim-path',
    'quest-for-qumran-mysteries-in-the-holy-land',
    # Longest posts
    'why-is-it-called-old-testament-and-new-testament',
    # Sacred sites category
    'exploring-biblical-archaeology-uncovering-ancient-sites',
    # Ark of Covenant (tons of these)
    'replicas-in-exile-the-quest-for-the-real-ark-of-the-covenant',
    # Mid-range
    'jerusalem-temple-foundations-finally-discovered',
]

for p in pub:
    if p['slug'] in slugs_wanted:
        samples.append(p)

print(f"Sampling {len(samples)} posts for quality check\n")

for p in samples:
    print("=" * 80)
    print(f"TITLE: {p['title']}")
    print(f"SLUG:  {p['slug']}")
    print(f"WORDS: {p['word_count']}")
    cats = [c['label'] for c in p['categories'] if c['domain'] == 'category']
    print(f"CATS:  {', '.join(cats)}")
    print(f"\nFIRST 800 CHARS:")
    print(p['content_preview'][:800])
    print()
