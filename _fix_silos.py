"""Fix silo assignment using title + content keywords, not just WP categories."""
import json
import re

with open(r"D:\dev\projects\diggingscriptures\_keepers.json", "r", encoding="utf-8") as f:
    keepers = json.load(f)

# Keyword-based silo rules (checked in priority order)
SILO_RULES = [
    # SITES — sacred places, cities, archaeological sites
    ('sites', [
        r'\bjerusalem\b', r'\btemple mount\b', r'\bqumran\b', r'\bjericho\b',
        r'\bpilgrim route', r'\bpilgrim path', r'\bein gedi\b', r'\bgalilee\b',
        r'\bjudean\b', r'\bdead sea\b', r'\bcity of david\b', r'\bmount\b',
        r'\bbiblical site', r'\bsacred site', r'\bholy land\b', r'\bbiblical town',
        r'\bancient jerusalem\b', r'\btemple foundation', r'\btemple mount\b',
        r'\bexcavation site', r'\bdig site', r'\bbiblical cit',
    ]),
    # ARTIFACTS — objects, relics, seals, scrolls, ark
    ('artifacts', [
        r'\bark of the covenant\b', r'\bdead sea scroll', r'\bscroll\b',
        r'\bartifact', r'\brelic\b', r'\bseal\b', r'\bcoin\b', r'\bjar\b',
        r'\btablet\b', r'\binscription\b', r'\bpapyrus\b', r'\bcodex\b',
        r'\bmanuscript\b', r'\bpottery\b', r'\bceramic', r'\bvessel\b',
    ]),
    # SCRIPTURE — Bible texts, languages, translations, manuscripts
    ('scripture', [
        r'\bold testament\b', r'\bnew testament\b', r'\bbible\b', r'\bscripture\b',
        r'\bhebrew\b', r'\bgreek\b', r'\baramaic\b', r'\btorah\b', r'\bseptuagint\b',
        r'\bcanon\b', r'\bgospel\b', r'\bsynoptic\b', r'\binterpolation\b',
        r'\btranslat', r'\blanguage\b.*\b(testament|bible|written)\b',
        r'\bwritten in\b', r'\boriginal\b.*\b(bible|text|language)\b',
        r'\bethiopian bible\b', r'\bgutenberg\b', r'\bking james\b',
    ]),
    # METHODS — archaeology techniques, dating, technology, careers
    ('methods', [
        r'\barchaeolog(y|ist|ical)\b.*\b(guide|beginner|career|degree|tip)',
        r'\bexcavation technique', r'\bdating method', r'\blidar\b',
        r'\b3d (scan|model)', r'\bground.penetrating radar\b', r'\bdna\b',
        r'\bscanning\b', r'\btechnolog\b.*\barchaeolog',
        r'\bbecomi?n?g\b.*\barchaeolog', r'\bdegree\b.*\barchaeolog',
    ]),
    # FAITH — worship, theology, rituals, religious practices
    ('faith', [
        r'\bworship\b', r'\britual\b', r'\btheolog', r'\bfaith\b',
        r'\bprayer\b', r'\bpriestl?y?\b', r'\bsacred\b.*\b(craft|oil|practice)',
        r'\bfeast\b', r'\bpurif', r'\bceremon',
        r'\bprophe(t|cy|tic)\b', r'\bmoral\b', r'\bethic',
    ]),
    # HISTORY — civilizations, empires, historical narratives (default fallback)
    ('history', [
        r'\bancient\b', r'\bhistor', r'\bcivilizat', r'\bempire\b',
        r'\bking\b', r'\bsolomon\b', r'\bdavid\b', r'\bexodus\b',
    ]),
]

def assign_silo_by_keywords(title, categories):
    """Assign silo by matching title against keyword patterns."""
    text = title.lower()
    # Also use categories as signal
    cat_text = ' '.join(categories).lower()
    combined = text + ' ' + cat_text
    
    for silo, patterns in SILO_RULES:
        for pattern in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return silo
    return 'history'  # Default

# Re-assign silos
for p in keepers:
    p['silo'] = assign_silo_by_keywords(p['title'], p['categories'])

# Stats
from collections import Counter
silo_counts = Counter(p['silo'] for p in keepers)
print("REVISED SILO BREAKDOWN:")
for silo, count in silo_counts.most_common():
    avg_wc = sum(p['word_count'] for p in keepers if p['silo'] == silo) // count
    top3 = sorted([p for p in keepers if p['silo'] == silo], 
                  key=lambda x: -x['quality_score'])[:3]
    print(f"\n  {silo:>12}: {count:>4} posts  (avg {avg_wc}w)")
    for t in top3:
        print(f"    {'*' if t['indexed'] else ' '} [{t['quality_score']}] {t['slug'][:65]}")

# Save updated keepers
with open(r"D:\dev\projects\diggingscriptures\_keepers.json", "w", encoding="utf-8") as f:
    json.dump(keepers, f, indent=2, ensure_ascii=False)
print(f"\nUpdated {len(keepers)} keepers in _keepers.json")

# Also update the full file
with open(r"D:\dev\projects\diggingscriptures\_keepers_full.json", "r", encoding="utf-8") as f:
    full = json.load(f)

slug_to_silo = {p['slug']: p['silo'] for p in keepers}
for p in full:
    p['silo'] = slug_to_silo.get(p['slug'], p['silo'])

with open(r"D:\dev\projects\diggingscriptures\_keepers_full.json", "w", encoding="utf-8") as f:
    json.dump(full, f, indent=2, ensure_ascii=False)
print(f"Updated {len(full)} keepers in _keepers_full.json")
