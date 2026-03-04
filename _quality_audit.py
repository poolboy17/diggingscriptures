"""
Brutal quality audit — find the content NOT worth keeping.
Checks: near-duplicate topics, ultra-generic titles, 
topic cannibalization, thin content, filler patterns.
"""
import json
import re
from collections import Counter, defaultdict

with open(r"D:\dev\projects\diggingscriptures\_keepers.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

print(f"Starting with {len(posts)} posts\n")

# ============================================================
# 1. NEAR-DUPLICATE TOPIC DETECTION
#    Strip filler words, compare core topic slugs
# ============================================================
FILLER_WORDS = {'exploring', 'unveiling', 'unearthing', 'discovering',
    'uncovering', 'unraveling', 'deciphering', 'unlocking', 'secrets',
    'mysteries', 'ancient', 'reveals', 'revealed', 'hidden', 'lost',
    'fascinating', 'remarkable', 'intriguing', 'captivating',
    'deep', 'dive', 'journey', 'through', 'into', 'from', 'about',
    'what', 'how', 'does', 'ever', 'guide', 'ultimate', 'comprehensive'}

def topic_key(title):
    """Extract core topic from title, stripping filler."""
    words = re.findall(r'[a-z]+', title.lower())
    core = [w for w in words if w not in FILLER_WORDS and len(w) > 2]
    return ' '.join(sorted(core))

# Group by topic key
topic_groups = defaultdict(list)
for p in posts:
    key = topic_key(p['title'])
    topic_groups[key].append(p)

# Find cannibalization clusters (same topic, multiple posts)
cannibal_clusters = {k: v for k, v in topic_groups.items() if len(v) > 1}

cannibal_post_count = sum(len(v) for v in cannibal_clusters.values())
cannibal_excess = sum(len(v) - 1 for v in cannibal_clusters.values())

print("=" * 80)
print(f"TOPIC CANNIBALIZATION: {len(cannibal_clusters)} topic clusters with multiple posts")
print(f"  Posts in cannibal clusters: {cannibal_post_count}")
print(f"  Excess posts (would keep 1 per cluster): {cannibal_excess}")
print("=" * 80)

# Show worst offenders
for key, group in sorted(cannibal_clusters.items(), key=lambda x: -len(x[1]))[:20]:
    print(f"\n  [{len(group)}x] Topic: '{key[:60]}'")
    for p in sorted(group, key=lambda x: -x['word_count']):
        print(f"    {p['word_count']:>5}w  Q{p['quality_score']:>2}  {p['slug'][:55]}")

# ============================================================
# 2. ULTRA-GENERIC TITLES (no specific topic)
# ============================================================
print("\n" + "=" * 80)
print("ULTRA-GENERIC TITLES (vague, no specific topic)")
print("=" * 80)

generic_patterns = [
    r'^(exploring|unveiling|unearthing|discovering|uncovering) (the )?(secrets?|mysteries?|wonders?) (of )?biblical archaeolog',
    r'^biblical archaeology[:\s]*(unveiling|unearthing|exploring|discovering)',
    r'^biblical archaeology and (ancient |its )',
    r'^biblical archaeology (unearthing|reveals?|investigation)',
]

generic_posts = []
for p in posts:
    title = p['title'].lower()
    for pat in generic_patterns:
        if re.match(pat, title):
            generic_posts.append(p)
            break

print(f"  Found {len(generic_posts)} ultra-generic posts:")
for p in sorted(generic_posts, key=lambda x: x['word_count'])[:20]:
    print(f"    {p['word_count']:>5}w  {p['title'][:65]}")

# ============================================================
# 3. Q&A FILLER (short "What is X" posts that add no depth)
# ============================================================
print("\n" + "=" * 80)
print("SHORT Q&A POSTS (<1100w, question-format title)")
print("=" * 80)

qa_posts = [p for p in posts if p['word_count'] < 1100 and 
            re.match(r'^(what|how|when|where|why|is|are|can|did|does|have|was|were)\b', 
                     p['title'].lower())]

print(f"  Found {len(qa_posts)} short Q&A posts:")
for p in sorted(qa_posts, key=lambda x: x['word_count'])[:20]:
    print(f"    {p['word_count']:>5}w  {p['title'][:65]}")

# ============================================================
# 4. ARK OF COVENANT SPAM — do we really need 38 Ark posts?
# ============================================================
print("\n" + "=" * 80)
print("ARK OF THE COVENANT SATURATION CHECK")
print("=" * 80)

ark_posts = [p for p in posts if re.search(r'\bark\b', p['title'].lower())]
print(f"  Posts with 'Ark' in title: {len(ark_posts)}")
print(f"  Total words: {sum(p['word_count'] for p in ark_posts):,}")
print(f"\n  By quality score:")
for p in sorted(ark_posts, key=lambda x: -x['quality_score'])[:10]:
    print(f"    Q{p['quality_score']:>2}  {p['word_count']:>5}w  {p['title'][:55]}")
print(f"  ...")
for p in sorted(ark_posts, key=lambda x: x['quality_score'])[:5]:
    print(f"    Q{p['quality_score']:>2}  {p['word_count']:>5}w  {p['title'][:55]}")

# ============================================================
# 5. OVERLY CREATIVE SLUGS (AI-generated fiction-style slugs)
# ============================================================
print("\n" + "=" * 80)
print("AI-FICTION SLUGS (overly narrative, not SEO-useful)")
print("=" * 80)

fiction_patterns = [
    r'enigma-of', r'mystique-of', r'enigmatic', r'haunted-tomb',
    r'nighttime-vigil', r'scribes-fleeting', r'exiled-hearts',
    r'whisper', r'melody', r'golden-veil', r'caretakers-glimpse',
    r'elderly-levites', r'humbled-nobles', r'idol-seizing',
    r'nation-in-crisis', r'kings-idolatry', r'desert-seekers',
    r'pre-battle-ceremony', r'prophetic-caution', r'levites-gilded',
    r'fiery-pillars', r'caravan-tales', r'vanished-expedition',
    r'royal-dispute', r'cherubim-throne', r'stable-trapdoor',
]

fiction_posts = [p for p in posts if any(
    re.search(pat, p['slug']) for pat in fiction_patterns)]

print(f"  Found {len(fiction_posts)} fiction-style slug posts:")
for p in fiction_posts[:15]:
    print(f"    {p['word_count']:>5}w  {p['slug'][:65]}")

# ============================================================
# 6. FINAL RECOMMENDATION
# ============================================================
# Flag posts to CUT
cut_slugs = set()
cut_reasons = defaultdict(list)

# a) From cannibal clusters — keep only the longest post per cluster
for key, group in cannibal_clusters.items():
    best = max(group, key=lambda x: x['word_count'])
    for p in group:
        if p['slug'] != best['slug'] and not p['indexed']:
            cut_slugs.add(p['slug'])
            cut_reasons[p['slug']].append(f"cannibal-dupe of {best['slug'][:40]}")

# b) Fiction-style slugs (unless they're indexed or >2000w)
for p in fiction_posts:
    if not p['indexed'] and p['word_count'] < 2000:
        cut_slugs.add(p['slug'])
        cut_reasons[p['slug']].append("fiction-style slug, low SEO value")

# c) Ultra-generic titles under 1500w
for p in generic_posts:
    if not p['indexed'] and p['word_count'] < 1500:
        cut_slugs.add(p['slug'])
        cut_reasons[p['slug']].append("ultra-generic title, thin")

# d) Short Q&A that overlap with longer posts
for p in qa_posts:
    if not p['indexed'] and p['word_count'] < 1000:
        cut_slugs.add(p['slug'])
        cut_reasons[p['slug']].append("short Q&A filler")

final_keepers = [p for p in posts if p['slug'] not in cut_slugs]
final_cuts = [p for p in posts if p['slug'] in cut_slugs]

print("\n" + "=" * 80)
print("FINAL RECOMMENDATION")
print("=" * 80)
print(f"  KEEP:  {len(final_keepers)} posts ({sum(p['word_count'] for p in final_keepers):,} words)")
print(f"  CUT:   {len(final_cuts)} posts ({sum(p['word_count'] for p in final_cuts):,} words)")
print(f"  Google-indexed preserved: {sum(1 for p in final_keepers if p['indexed'])}")

# Cut reason breakdown
reason_counts = Counter()
for slug, reasons in cut_reasons.items():
    for r in reasons:
        reason_counts[r.split(' of ')[0] if ' of ' in r else r] += 1

print(f"\n  CUT REASONS:")
for reason, count in reason_counts.most_common():
    print(f"    {count:>4}x  {reason}")

# Silo breakdown of final keepers
silo_counts = Counter(p['silo'] for p in final_keepers)
print(f"\n  FINAL SILO BREAKDOWN:")
for silo, count in silo_counts.most_common():
    avg_wc = sum(p['word_count'] for p in final_keepers if p['silo'] == silo) // count
    print(f"    {silo:>15}: {count:>4} posts  (avg {avg_wc}w)")

# Save final keeper slugs
with open(r"D:\dev\projects\diggingscriptures\_final_keepers.json", "w", encoding="utf-8") as f:
    json.dump([p['slug'] for p in final_keepers], f, indent=2)

with open(r"D:\dev\projects\diggingscriptures\_cuts.json", "w", encoding="utf-8") as f:
    json.dump([{'slug': p['slug'], 'title': p['title'], 'words': p['word_count'],
                'reasons': cut_reasons.get(p['slug'], [])} for p in final_cuts], f, indent=2)

print(f"\n  Saved to _final_keepers.json and _cuts.json")
