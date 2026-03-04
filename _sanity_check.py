#!/usr/bin/env python3
"""
Sanity Check — Process & Writer Alignment Audit
Checks for gaps between what the writer config promises,
what the pipeline checks, and what actually exists in articles.
"""
import os, re, json
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.join(BASE, "src", "content", "research")
CATS = ["biblical-archaeology","scripture","excavations","artifacts","faith"]

def parse_fm(fp):
    with open(fp, "r", encoding="utf-8") as f:
        raw = f.read()
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    fm = {}
    for line in parts[1].strip().split("\n"):
        s = line.strip()
        if ":" in s and not s.startswith("-") and not s.startswith("#"):
            k = s[:s.index(":")].strip()
            v = s[s.index(":")+1:].strip().strip('"').strip("'")
            fm[k] = v
    return fm, parts[2]

def strip_md(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    return text.strip()

issues = []
stats = Counter()

print("=" * 70)
print("SANITY CHECK — Process & Writer Alignment Audit")
print("=" * 70)

# Load all articles
articles = []
for cat in CATS:
    d = os.path.join(RESEARCH, cat)
    if not os.path.isdir(d):
        continue
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".md"):
            continue
        fp = os.path.join(d, fn)
        fm, body = parse_fm(fp)
        plain = strip_md(body)
        wc = len(plain.split())
        h2s = re.findall(r'^##\s+(.+)$', body, re.MULTILINE)
        h3s = re.findall(r'^###\s+(.+)$', body, re.MULTILINE)
        ilinks = re.findall(r'\]\((/[^)]+)\)', body)
        articles.append({
            'slug': fn[:-3], 'cat': cat, 'fp': fp,
            'fm': fm, 'body': body, 'plain': plain,
            'wc': wc, 'h2s': h2s, 'h3s': h3s, 'ilinks': ilinks,
        })

print(f"\nLoaded {len(articles)} articles\n")

# ── CHECK 1: FAQ Quality ──────────────────────────────────────
print("--- CHECK 1: FAQ SECTION QUALITY ---")
no_faq = []
generic_faq = []
good_faq = []
for a in articles:
    has_faq = bool(re.search(r'^##\s+Frequently Asked', a['body'], re.M|re.I))
    if not has_faq:
        no_faq.append(a['slug'])
        stats['no_faq'] += 1
        continue
    # Check if FAQ answers are generic (template) vs specific
    faq_section = a['body'][a['body'].lower().rfind('## frequently'):]
    # Generic indicator: "represents an important area of study"
    if 'represents an important area of study' in faq_section:
        generic_faq.append(a['slug'])
        stats['generic_faq'] += 1
    else:
        good_faq.append(a['slug'])
        stats['good_faq'] += 1

print(f"  No FAQ:      {len(no_faq)}")
print(f"  Generic FAQ: {len(generic_faq)} (template answers, not article-specific)")
print(f"  Good FAQ:    {len(good_faq)} (appears customized)")
if generic_faq:
    issues.append(f"MEDIUM: {len(generic_faq)} articles have generic template FAQ answers")

# ── CHECK 2: Opening Paragraph Quality ────────────────────────
print("\n--- CHECK 2: OPENING PARAGRAPH QUALITY ---")
weak_opens = []
strong_opens = []
definitional_verbs = r'\b(?:is|are|was|were|refers? to|dates? to|represents?|means?|denotes?)\b'
for a in articles:
    # Get first paragraph (skip frontmatter whitespace)
    body_stripped = a['body'].strip()
    paras = [p.strip() for p in body_stripped.split('\n\n') if len(p.strip()) > 30]
    if not paras:
        weak_opens.append(a['slug'])
        continue
    first_p = strip_md(paras[0])
    first_sentences = re.split(r'(?<=[.!?])\s+', first_p)[:2]
    opener = ' '.join(first_sentences)
    if len(opener) >= 40 and re.search(definitional_verbs, opener, re.I):
        strong_opens.append(a['slug'])
    else:
        weak_opens.append(a['slug'])

print(f"  Strong openers: {len(strong_opens)} (definitional verb in first 2 sentences)")
print(f"  Weak openers:   {len(weak_opens)} (narrative/vague start)")
if weak_opens:
    issues.append(f"HIGH: {len(weak_opens)} articles have weak opening paragraphs (no definitional verb)")

# ── CHECK 3: Question-Format Headings ─────────────────────────
print("\n--- CHECK 3: QUESTION-FORMAT HEADINGS ---")
q_counts = Counter()
no_questions = []
for a in articles:
    all_headings = a['h2s'] + a['h3s']
    q_headings = [h for h in all_headings if '?' in h or
                  h.lower().startswith(('what','who','where','when','why','how','does','did','can','is','are'))]
    q_counts[len(q_headings)] += 1
    if len(q_headings) < 2:
        no_questions.append(a['slug'])

print(f"  0 question headings: {q_counts[0]} articles")
print(f"  1 question heading:  {q_counts[1]} articles")
print(f"  2 question headings: {q_counts[2]} articles")
print(f"  3+ question headings: {sum(v for k,v in q_counts.items() if k >= 3)} articles")
# Note: FAQ H3s count here, so post-FAQ articles should have >= 3
if no_questions:
    issues.append(f"MEDIUM: {len(no_questions)} articles have <2 question-format headings (writer config requires >=2)")

# ── CHECK 4: Definition Sentences ─────────────────────────────
print("\n--- CHECK 4: DEFINITION SENTENCES ---")
no_defs = []
for a in articles:
    defs = re.findall(r'(?:^|\. )[A-Z][a-z]+ (?:is|refers to|means|was|are) [a-z]', a['plain'])
    if len(defs) < 1:
        no_defs.append(a['slug'])

print(f"  Articles with 0 definition sentences: {len(no_defs)}")
if no_defs:
    issues.append(f"LOW: {len(no_defs)} articles have zero 'X is Y' definition patterns")

# ── CHECK 5: List Structure ───────────────────────────────────
print("\n--- CHECK 5: LIST STRUCTURE ---")
no_lists = []
for a in articles:
    bullets = len(re.findall(r'^[\s]*[-*+]\s', a['body'], re.M))
    numbered = len(re.findall(r'^[\s]*\d+[.)]\s', a['body'], re.M))
    if bullets + numbered < 1:
        no_lists.append(a['slug'])

print(f"  Articles with 0 lists: {len(no_lists)}")
if no_lists:
    issues.append(f"MEDIUM: {len(no_lists)} articles have zero bulleted/numbered lists")

# ── CHECK 6: Internal Links ──────────────────────────────────
print("\n--- CHECK 6: INTERNAL LINKS ---")
orphaned = []
low_links = []
for a in articles:
    n = len(a['ilinks'])
    if n == 0:
        orphaned.append(a['slug'])
    elif n < 3:
        low_links.append(a['slug'])

print(f"  Zero internal links: {len(orphaned)} (orphaned)")
print(f"  1-2 internal links:  {len(low_links)} (below writer config minimum of 3)")
if orphaned:
    issues.append(f"CRITICAL: {len(orphaned)} articles have ZERO internal links (orphaned)")
if low_links:
    issues.append(f"HIGH: {len(low_links)} articles have <3 internal links (writer config requires >=3)")

# ── CHECK 7: Frontmatter Completeness ─────────────────────────
print("\n--- CHECK 7: FRONTMATTER COMPLETENESS ---")
fm_gaps = Counter()
for a in articles:
    fm = a['fm']
    for field in ['title', 'description', 'category', 'image', 'imageAlt', 'pubDate']:
        if not fm.get(field):
            fm_gaps[field] += 1

print(f"  Missing fields across {len(articles)} articles:")
for field, count in fm_gaps.most_common():
    print(f"    {field}: {count} missing")
    if field in ('title', 'description', 'category') and count > 0:
        issues.append(f"CRITICAL: {count} articles missing required field '{field}'")
    elif count > 0:
        issues.append(f"LOW: {count} articles missing optional field '{field}'")

# ── CHECK 8: Banned Phrases Still Present ─────────────────────
print("\n--- CHECK 8: BANNED PHRASES ---")
BANNED = [
    "in this article", "in this post", "in this guide",
    "without further ado", "it goes without saying",
    "needless to say", "at the end of the day",
    "it is important to note", "it is worth noting",
    "in today's world", "in today's day and age",
    "since the dawn of time", "throughout human history",
    "buckle up", "dive in", "let's dive",
    "game changer", "game-changer",
    "you won't believe", "mind-blowing",
    "in conclusion",
]
banned_found = Counter()
for a in articles:
    for phrase in BANNED:
        if re.search(r'\b' + re.escape(phrase) + r'\b', a['body'], re.I):
            banned_found[phrase] += 1

if banned_found:
    total_banned = sum(banned_found.values())
    print(f"  {total_banned} banned phrase occurrences found:")
    for phrase, count in banned_found.most_common(10):
        print(f"    '{phrase}': {count}")
    issues.append(f"HIGH: {total_banned} banned phrase occurrences still in articles")
else:
    print(f"  Clean — no banned phrases found")

# ── CHECK 9: Writer Config vs Pipeline Alignment ─────────────
print("\n--- CHECK 9: CONFIG ↔ PIPELINE ALIGNMENT ---")
alignment_gaps = []

# Read writer config
wc_path = os.path.join(BASE, "docs", "ARTICLE-WRITER-CONFIG.md")
with open(wc_path, "r", encoding="utf-8") as f:
    wc_text = f.read()

# Read pipeline
pipe_path = os.path.join(BASE, "semantic-pipe-research.py")
with open(pipe_path, "r", encoding="utf-8") as f:
    pipe_text = f.read()

# Check: writer config requires >=3 internal links, does pipeline check?
if "internal_links" not in pipe_text and "internal link" not in pipe_text.lower():
    # SXO score_sxo does check internal links
    if "get_internal_links" in pipe_text:
        print("  [OK] Pipeline checks internal links (via SXO scoring)")
    else:
        alignment_gaps.append("Writer requires >=3 internal links but pipeline doesn't check")
else:
    print("  [OK] Pipeline checks internal links")

# Check: writer config bans "in conclusion" but pipeline BANNED_PHRASES list?
if "'in conclusion'" not in pipe_text and '"in conclusion"' not in pipe_text:
    alignment_gaps.append("Writer bans 'in conclusion' but pipeline BANNED_PHRASES list doesn't include it")
else:
    print("  [OK] 'in conclusion' in pipeline banned list")

# Check: writer config bans "sacred duty", "spiritual awakening", "blessed"
for phrase in ["sacred duty", "spiritual awakening"]:
    if phrase not in pipe_text.lower():
        alignment_gaps.append(f"Writer bans '{phrase}' but pipeline doesn't check for it")

# Check: writer config requires >=3 dates, does pipeline score this?
if "years" in pipe_text:
    print("  [OK] Pipeline scores date/year density (GEO layer)")
else:
    alignment_gaps.append("Writer requires >=3 dates but pipeline doesn't check")

# Check: writer config requires >=3 named figures, pipeline?
if "namedPeople" in pipe_text or "named_people" in pipe_text:
    print("  [OK] Pipeline scores named people (legacy scores)")
else:
    alignment_gaps.append("Writer requires >=3 named figures but pipeline doesn't check")

# Check: does pipeline flag articles below word count minimum?
if "word_count" in pipe_text or "wc" in pipe_text:
    print("  [OK] Pipeline tracks word count")
else:
    alignment_gaps.append("Pipeline doesn't track word count")

# Check: does pipeline enforce opening paragraph quality (not just score)?
if "harden" in pipe_text.lower() and "opener" in pipe_text.lower():
    print("  [OK] Pipeline has opener hardening")
else:
    if "opening" in pipe_text.lower() or "first_p" in pipe_text:
        print("  [PARTIAL] Pipeline SCORES openers but doesn't AUTO-FIX them")
        alignment_gaps.append("Pipeline scores opening paragraph quality but has no auto-fix (only FAQ injection exists)")
    else:
        alignment_gaps.append("Pipeline doesn't check opening paragraph quality at all")

# Check: writer config requires >=2 question headings, does pipeline enforce?
if "question_h2" in pipe_text or "question_heading" in pipe_text:
    print("  [PARTIAL] Pipeline SCORES question headings but doesn't inject them")
    alignment_gaps.append("Pipeline scores question headings but has no auto-fix — only FAQ H3s count")
else:
    alignment_gaps.append("Pipeline doesn't check question-format headings")

# Check: writer config requires lists, does pipeline enforce?
if "list_items" in pipe_text or "bullet" in pipe_text:
    print("  [PARTIAL] Pipeline SCORES list presence but doesn't inject them")
else:
    alignment_gaps.append("Pipeline doesn't check list structure")

for gap in alignment_gaps:
    print(f"  [GAP] {gap}")
    issues.append(f"ALIGNMENT: {gap}")

# ── CHECK 10: Duplicate/Near-Duplicate Titles ─────────────────
print("\n--- CHECK 10: DUPLICATE TITLES ---")
titles = Counter()
for a in articles:
    t = a['fm'].get('title', '').lower().strip()
    if t:
        titles[t] += 1
dupes = {t: c for t, c in titles.items() if c > 1}
if dupes:
    print(f"  {len(dupes)} duplicate titles found:")
    for t, c in sorted(dupes.items(), key=lambda x: -x[1])[:10]:
        print(f"    [{c}x] {t[:60]}")
    issues.append(f"HIGH: {len(dupes)} duplicate titles across research articles")
else:
    print("  Clean — no duplicate titles")

# ── CHECK 11: Thin Content ────────────────────────────────────
print("\n--- CHECK 11: THIN CONTENT ---")
thin = [a for a in articles if a['wc'] < 500]
very_thin = [a for a in articles if a['wc'] < 300]
print(f"  <300 words: {len(very_thin)} articles")
print(f"  <500 words: {len(thin)} articles")
if very_thin:
    issues.append(f"CRITICAL: {len(very_thin)} articles under 300 words (thin content penalty risk)")
    for a in very_thin[:5]:
        print(f"    {a['wc']}w {a['slug'][:55]}")
if thin and not very_thin:
    issues.append(f"HIGH: {len(thin)} articles under 500 words")

# ── CHECK 12: H2 Count ────────────────────────────────────────
print("\n--- CHECK 12: H2 COUNT ---")
low_h2 = [a for a in articles if len(a['h2s']) < 3]
no_h2 = [a for a in articles if len(a['h2s']) == 0]
print(f"  0 H2s: {len(no_h2)} articles")
print(f"  <3 H2s: {len(low_h2)} articles")
if no_h2:
    issues.append(f"HIGH: {len(no_h2)} articles have ZERO H2 headings")

# ── CHECK 13: Image Coverage ──────────────────────────────────
print("\n--- CHECK 13: IMAGE COVERAGE ---")
no_image = [a for a in articles if not a['fm'].get('image')]
no_alt = [a for a in articles if a['fm'].get('image') and not a['fm'].get('imageAlt')]
print(f"  No image: {len(no_image)} articles")
print(f"  Image but no alt: {len(no_alt)} articles")
if no_image:
    issues.append(f"MEDIUM: {len(no_image)} articles missing hero image")
if no_alt:
    issues.append(f"LOW: {len(no_alt)} articles have image but no alt text")

# ═══════════════════════════════════════════════════════════════
# SUMMARY REPORT
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*70}")
print(f"ISSUES FOUND: {len(issues)}")
print(f"{'='*70}")
severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'ALIGNMENT']
for sev in severity_order:
    sev_issues = [i for i in issues if i.startswith(sev)]
    if sev_issues:
        print(f"\n  [{sev}]")
        for i in sev_issues:
            print(f"    {i}")

# Action items
print(f"\n{'='*70}")
print("RECOMMENDED ACTIONS (by impact):")
print(f"{'='*70}")
actions = []
if any('orphaned' in i.lower() or 'zero internal links' in i.lower() for i in issues):
    actions.append("1. [CRITICAL] Build internal link injector — orphaned articles hurt all 3 layers")
if any('generic template faq' in i.lower() for i in issues):
    actions.append("2. [HIGH] Improve FAQ generator — use article body content to generate specific answers instead of templates")
if any('weak opening' in i.lower() for i in issues):
    actions.append("3. [HIGH] Build opener hardener — rewrite first sentence to include definitional verb")
if any('banned phrase' in i.lower() for i in issues):
    actions.append("4. [HIGH] Re-run banned phrase cleaner — expand BANNED_PHRASES list to match writer config")
if any('duplicate titles' in i.lower() for i in issues):
    actions.append("5. [HIGH] Deduplicate titles — add suffix differentiators or merge thin duplicates")
if any('question-format headings' in i.lower() or 'question headings' in i.lower() for i in issues):
    actions.append("6. [MEDIUM] Convert 1-2 declarative H2s per article to question format")
if any('zero bulleted' in i.lower() or 'zero lists' in i.lower() for i in issues):
    actions.append("7. [MEDIUM] Inject at least one structured list per article")
if any("'in conclusion'" in i.lower() or 'sacred duty' in i.lower() for i in issues):
    actions.append("8. [MEDIUM] Sync pipeline BANNED_PHRASES with full writer config banned list")
for a in actions:
    print(f"  {a}")

print(f"\n{'='*70}")
print("AUDIT COMPLETE")
print(f"{'='*70}")
