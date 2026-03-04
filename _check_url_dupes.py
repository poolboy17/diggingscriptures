"""Check for duplicate permalinks across ALL content collections."""
import os
from collections import defaultdict

dist_dir = "dist"
urls = defaultdict(list)

for root, dirs, files in os.walk(dist_dir):
    for f in files:
        if f == "index.html":
            rel = os.path.relpath(root, dist_dir).replace("\\", "/")
            if rel == ".":
                rel = "/"
            else:
                rel = "/" + rel
            urls[rel].append(os.path.join(root, f))

# Find duplicates
dupes = {k: v for k, v in urls.items() if len(v) > 1}
print(f"Total unique URLs: {len(urls)}")
print(f"Duplicate URLs: {len(dupes)}")
for url, paths in sorted(dupes.items()):
    print(f"\n  DUPE: {url}")
    for p in paths:
        print(f"    -> {p}")

# Also check: do any research slugs match pilgrimage slugs?
print("\n--- CROSS-SILO SLUG COLLISION CHECK ---")
research_slugs = set()
pilgrimage_slugs = set()

for section in ["places", "routes", "stories", "context", "journeys"]:
    section_dir = os.path.join(dist_dir, section)
    if os.path.isdir(section_dir):
        for item in os.listdir(section_dir):
            item_path = os.path.join(section_dir, item)
            if os.path.isdir(item_path):
                pilgrimage_slugs.add(item)

for cat_dir in ["biblical-archaeology", "scripture", "excavations", "artifacts", "faith"]:
    full = os.path.join(dist_dir, "research", cat_dir)
    if os.path.isdir(full):
        for item in os.listdir(full):
            item_path = os.path.join(full, item)
            if os.path.isdir(item_path):
                research_slugs.add(item)

collisions = research_slugs & pilgrimage_slugs
print(f"Pilgrimage slugs: {len(pilgrimage_slugs)}")
print(f"Research slugs: {len(research_slugs)}")
print(f"Cross-silo collisions: {len(collisions)}")
for c in sorted(collisions):
    print(f"  COLLISION: {c}")

# Check for duplicates WITHIN research categories
print("\n--- RESEARCH INTRA-CATEGORY DUPE CHECK ---")
cat_slugs = defaultdict(list)
for cat_dir in ["biblical-archaeology", "scripture", "excavations", "artifacts", "faith"]:
    full = os.path.join(dist_dir, "research", cat_dir)
    if os.path.isdir(full):
        for item in os.listdir(full):
            if os.path.isdir(os.path.join(full, item)):
                cat_slugs[item].append(cat_dir)

cross_cat = {k: v for k, v in cat_slugs.items() if len(v) > 1}
print(f"Slugs appearing in multiple categories: {len(cross_cat)}")
for slug, cats in sorted(cross_cat.items()):
    print(f"  {slug} -> {', '.join(cats)}")
