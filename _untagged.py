"""Analyze the 366 untagged posts — what are they about?"""
import json
import re
from collections import Counter

with open(r"D:\dev\projects\diggingscriptures\_keepers.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

# Re-tag (same logic as before)
TOPIC_PATTERNS = {
    'old-testament': r'\bold testament\b', 'new-testament': r'\bnew testament\b',
    'bible-origins': r'\b(bible|biblical).*(origin|found|first|oldest|kept)\b',
    'dead-sea-scrolls': r'\bdead sea scroll', 'languages': r'\b(hebrew|greek|aramaic)\b.*\b(written|language|original)\b',
    'manuscripts': r'\b(manuscript|papyrus|codex|scroll|parchment)\b',
    'canon': r'\b(canon|apocryph|interpolat|synoptic)\b',
    'jerusalem': r'\bjerusalem\b', 'temple-mount': r'\btemple mount\b',
    'qumran': r'\bqumran\b', 'jericho': r'\bjericho\b',
    'temple-general': r'\btemple\b(?! mount)',
    'ark-covenant': r'\bark of the covenant\b|\bark\b.*\bcovenant\b',
    'ark-power': r'\bark\b.*\b(power|divine|sacred|glory)\b',
    'seals': r'\bseal\b', 'pottery': r'\b(potter|ceramic|jar|vessel)\b',
    'relics': r'\brelic\b', 'artifacts-general': r'\bartifact\b',
    'technology': r'\b(lidar|3d|scanning|radar|dna|digital|technolog)\b',
    'careers': r'\b(degree|career|becoming|aspiring|archaeologist)\b',
    'worship': r'\bworship\b', 'rituals': r'\britual\b',
    'prophecy': r'\bprophe(t|cy|tic)\b', 'ethics-morality': r'\b(ethic|moral|justice|mercy)\b',
    'warfare': r'\b(battle|war|conquest|fortress|defense|gate)\b',
    'trade-commerce': r'\b(trade|commerce|market|merchant)\b',
}

for p in posts:
    text = (p['title'] + ' ' + p['excerpt']).lower()
    tags = [tag for tag, pat in TOPIC_PATTERNS.items() if re.search(pat, text, re.IGNORECASE)]
    p['topic_tags'] = tags

untagged = [p for p in posts if not p['topic_tags']]
print(f"UNTAGGED POSTS: {len(untagged)}\n")

# Look for common words in untagged titles
title_words = Counter()
for p in untagged:
    words = re.findall(r'\b[a-z]{4,}\b', p['title'].lower())
    for w in words:
        title_words[w] += 1

print("Most common words in untagged titles:")
for word, count in title_words.most_common(40):
    print(f"  {word:>20}: {count}")

# Sample untagged by word count tiers
print(f"\n\nSAMPLE UNTAGGED >2000w ({len([p for p in untagged if p['word_count'] > 2000])}):")
for p in sorted([p for p in untagged if p['word_count'] > 2000], key=lambda x: -x['word_count'])[:15]:
    print(f"  {p['word_count']:>5}w  {p['title'][:70]}")

print(f"\nSAMPLE UNTAGGED 1000-2000w ({len([p for p in untagged if 1000 <= p['word_count'] <= 2000])}):")
for p in sorted([p for p in untagged if 1000 <= p['word_count'] <= 2000], key=lambda x: -x['word_count'])[:15]:
    print(f"  {p['word_count']:>5}w  {p['title'][:70]}")

print(f"\nSAMPLE UNTAGGED <1000w ({len([p for p in untagged if p['word_count'] < 1000])}):")
for p in sorted([p for p in untagged if p['word_count'] < 1000], key=lambda x: -x['word_count'])[:15]:
    print(f"  {p['word_count']:>5}w  {p['title'][:70]}")
