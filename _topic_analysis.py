"""
Deep topic analysis — cluster posts by actual content themes.
Uses title + H2 headings + excerpt to identify real topic clusters.
"""
import json
import re
from collections import Counter, defaultdict

with open(r"D:\dev\projects\diggingscriptures\_keepers.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

# Topic detection patterns — each returns a list of topic tags
TOPIC_PATTERNS = {
    # BIBLE TEXTS
    'old-testament': r'\bold testament\b',
    'new-testament': r'\bnew testament\b',
    'bible-origins': r'\b(bible|biblical).*(origin|found|first|oldest|kept)\b',
    'bible-changes': r'\b(bible|biblical).*(change|alter|translat|version)\b',
    'dead-sea-scrolls': r'\bdead sea scroll',
    'languages': r'\b(hebrew|greek|aramaic)\b.*\b(written|language|original)\b',
    'manuscripts': r'\b(manuscript|papyrus|codex|scroll|parchment)\b',
    'canon': r'\b(canon|apocryph|interpolat|synoptic)\b',
    'torah': r'\btorah\b',
    'septuagint': r'\bseptuagint\b',
    'ethiopian-bible': r'\bethiopian bible\b',
    'gutenberg': r'\bgutenberg\b',
    'oral-tradition': r'\boral tradition\b',
    
    # PLACES
    'jerusalem': r'\bjerusalem\b',
    'temple-mount': r'\btemple mount\b',
    'qumran': r'\bqumran\b',
    'jericho': r'\bjericho\b',
    'dead-sea-region': r'\bdead sea\b(?! scroll)',
    'city-of-david': r'\bcity of david\b',
    'galilee': r'\bgalilee\b',
    'jordan': r'\bjordan\b(?! crossing)',
    'ein-gedi': r'\bein gedi\b',
    'judean': r'\bjudean\b',
    'holy-land': r'\bholy land\b',
    
    # TEMPLE
    'first-temple': r'\bfirst temple\b',
    'second-temple': r'\bsecond temple\b',
    'temple-general': r'\btemple\b(?! mount)',
    'temple-construction': r'\btemple\b.*\b(construct|build|foundation|architect)\b',
    'temple-worship': r'\btemple\b.*\b(worship|ritual|sacred|vessel|artifact)\b',
    'temple-treasury': r'\btemple\b.*\b(treasur|storage|archive|seal)\b',
    
    # ARK OF THE COVENANT
    'ark-covenant': r'\bark of the covenant\b|\bark\b.*\bcovenant\b',
    'ark-quest': r'\bark\b.*\b(quest|search|find|hidden|lost|resting)\b',
    'ark-power': r'\bark\b.*\b(power|divine|sacred|glory)\b',
    
    # ARTIFACTS & OBJECTS
    'seals': r'\bseal\b',
    'coins': r'\bcoin\b',
    'pottery': r'\b(potter|ceramic|jar|vessel)\b',
    'inscriptions': r'\binscription\b',
    'relics': r'\brelic\b',
    'artifacts-general': r'\bartifact\b',
    
    # ARCHAEOLOGY METHODS & CAREERS
    'dating-methods': r'\b(dating method|carbon.dat|radiocarbon|modern dating)\b',
    'excavation': r'\bexcavation\b.*\b(technique|method|project)\b',
    'technology': r'\b(lidar|3d|scanning|radar|dna|digital|technolog)\b',
    'careers': r'\b(degree|career|becoming|aspiring|archaeologist)\b(?!.*\bdiscov)',
    'famous-archaeologists': r'\b(kathleen kenyon|albright|pioneer|prominent)\b.*archaeolog',
    
    # FAITH & THEOLOGY
    'worship': r'\bworship\b',
    'rituals': r'\britual\b',
    'prophecy': r'\bprophe(t|cy|tic)\b',
    'theology': r'\btheolog\b',
    'ethics-morality': r'\b(ethic|moral|justice|mercy)\b',
    'pilgrimage': r'\bpilgrim\b',
    
    # HISTORY & CIVILIZATIONS
    'ancient-cities': r'\bancient\b.*\b(cit|town|settlement)\b',
    'kings': r'\b(king|solomon|david|herod)\b.*\b(palace|reign|era)\b',
    'trade-commerce': r'\b(trade|commerce|market|merchant)\b',
    'warfare': r'\b(battle|war|conquest|fortress|defense|gate)\b',
}

# Tag every post
for p in posts:
    text = (p['title'] + ' ' + p['excerpt']).lower()
    tags = []
    for tag, pattern in TOPIC_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            tags.append(tag)
    p['topic_tags'] = tags

# Count tag frequency
tag_counts = Counter()
for p in posts:
    for t in p['topic_tags']:
        tag_counts[t] += 1

print("TOPIC TAG FREQUENCY (across 776 posts):")
print("=" * 60)
for tag, count in tag_counts.most_common():
    bar = '#' * (count // 5)
    print(f"  {tag:>25}: {count:>4}  {bar}")

# Group into mega-clusters
CLUSTERS = {
    'BIBLE_TEXTS': ['old-testament', 'new-testament', 'bible-origins', 'bible-changes',
                    'dead-sea-scrolls', 'languages', 'manuscripts', 'canon', 'torah',
                    'septuagint', 'ethiopian-bible', 'gutenberg', 'oral-tradition'],
    'SACRED_PLACES': ['jerusalem', 'temple-mount', 'qumran', 'jericho', 'dead-sea-region',
                      'city-of-david', 'galilee', 'jordan', 'ein-gedi', 'judean', 'holy-land'],
    'THE_TEMPLE': ['first-temple', 'second-temple', 'temple-general', 'temple-construction',
                   'temple-worship', 'temple-treasury'],
    'ARK_OF_COVENANT': ['ark-covenant', 'ark-quest', 'ark-power'],
    'ARTIFACTS': ['seals', 'coins', 'pottery', 'inscriptions', 'relics', 'artifacts-general'],
    'METHODS_CAREERS': ['dating-methods', 'excavation', 'technology', 'careers',
                        'famous-archaeologists'],
    'FAITH_THEOLOGY': ['worship', 'rituals', 'prophecy', 'theology', 'ethics-morality',
                       'pilgrimage'],
    'HISTORY': ['ancient-cities', 'kings', 'trade-commerce', 'warfare'],
}

print("\n\nMEGA-CLUSTER DISTRIBUTION:")
print("=" * 60)
for cluster, tags in CLUSTERS.items():
    # Count posts that have at least one tag in this cluster
    cluster_posts = [p for p in posts if any(t in tags for t in p['topic_tags'])]
    avg_wc = sum(p['word_count'] for p in cluster_posts) // max(len(cluster_posts), 1)
    print(f"\n  {cluster}: {len(cluster_posts)} posts (avg {avg_wc}w)")
    # Sub-tag breakdown
    for tag in tags:
        c = tag_counts.get(tag, 0)
        if c > 0:
            print(f"    {tag:>25}: {c}")

# Untagged posts
untagged = [p for p in posts if not p['topic_tags']]
print(f"\n  UNTAGGED: {len(untagged)} posts")
if untagged[:10]:
    for p in untagged[:10]:
        print(f"    {p['slug'][:60]}")
