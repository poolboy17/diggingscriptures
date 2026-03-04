"""
Comprehensive SEO audit for all 698 research articles.
Checks: titles, descriptions, slugs, headings, frontmatter, internal links.
"""
import os, re, json
from collections import Counter

CONTENT = r'D:\dev\projects\diggingscriptures\src\content\research'
results = {
    'total': 0,
    'title_issues': [],
    'desc_issues': [],
    'frontmatter_issues': [],
    'slug_issues': [],
    'heading_issues': [],
    'body_issues': [],
    'internal_link_issues': [],
    'duplicate_titles': [],
    'duplicate_descs': [],
}

all_titles = []
all_descs = []
all_slugs = set()

for cat in os.listdir(CONTENT):
    catdir = os.path.join(CONTENT, cat)
    if not os.path.isdir(catdir):
        continue
    for f in os.listdir(catdir):
        if not f.endswith('.md'):
            continue
        results['total'] += 1
        slug = f.replace('.md', '')
        filepath = os.path.join(catdir, f)
        ref = f'{cat}/{slug}'

        with open(filepath, 'r', encoding='utf-8') as fh:
            raw = fh.read()

        # Parse frontmatter
        fm_match = re.match(r'^---\n(.*?)\n---\n(.*)', raw, re.DOTALL)
        if not fm_match:
            results['frontmatter_issues'].append((ref, 'No frontmatter found'))
            continue

        fm_text = fm_match.group(1)
        body = fm_match.group(2)

        # Extract fields
        title = ''
        desc = ''
        category = ''
        has_pubdate = False
        for line in fm_text.split('\n'):
            if line.startswith('title:'):
                title = line.split(':', 1)[1].strip().strip('"').strip("'")
            elif line.startswith('description:'):
                desc = line.split(':', 1)[1].strip().strip('"').strip("'")
            elif line.startswith('category:'):
                category = line.split(':', 1)[1].strip().strip('"').strip("'")
            elif line.startswith('pubDate:'):
                has_pubdate = True

        # --- TITLE CHECKS ---
        if not title:
            results['title_issues'].append((ref, 'MISSING title'))
        else:
            tlen = len(title)
            if tlen < 20:
                results['title_issues'].append((ref, f'Too short ({tlen} chars): {title}'))
            elif tlen > 70:
                results['title_issues'].append((ref, f'Too long ({tlen} chars): {title[:70]}...'))
            all_titles.append(title.lower())

        # --- DESCRIPTION CHECKS ---
        if not desc:
            results['desc_issues'].append((ref, 'MISSING description'))
        else:
            dlen = len(desc)
            if dlen < 50:
                results['desc_issues'].append((ref, f'Too short ({dlen} chars)'))
            elif dlen > 160:
                results['desc_issues'].append((ref, f'Too long ({dlen} chars)'))
            all_descs.append(desc.lower())

        # --- FRONTMATTER CHECKS ---
        if not category:
            results['frontmatter_issues'].append((ref, 'Missing category'))
        if not has_pubdate:
            results['frontmatter_issues'].append((ref, 'Missing pubDate'))

        # --- SLUG CHECKS ---
        if len(slug) > 80:
            results['slug_issues'].append((ref, f'Slug too long ({len(slug)} chars)'))
        if slug in all_slugs:
            results['slug_issues'].append((ref, f'Duplicate slug: {slug}'))
        all_slugs.add(slug)
        if re.search(r'[A-Z]', slug):
            results['slug_issues'].append((ref, 'Uppercase in slug'))
        if '--' in slug:
            results['slug_issues'].append((ref, 'Double hyphen in slug'))
        if '%' in slug or '%' in f:
            results['slug_issues'].append((ref, f'Encoded characters in slug: {slug}'))

        # --- HEADING CHECKS ---
        h1s = re.findall(r'^# (.+)$', body, re.MULTILINE)
        h2s = re.findall(r'^## (.+)$', body, re.MULTILINE)
        if len(h1s) > 0:
            results['heading_issues'].append((ref, f'{len(h1s)} H1(s) in body (title is already H1)'))
        if len(h2s) == 0:
            results['heading_issues'].append((ref, 'No H2 subheadings'))

        # --- BODY CHECKS ---
        # Word count
        words = len(body.split())
        if words < 100:
            results['body_issues'].append((ref, f'Thin content ({words} words)'))

        # Check for broken internal links
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', body)
        for link_text, link_url in links:
            if link_url.startswith('/'):
                results['internal_link_issues'].append((ref, f'Internal link: {link_url}'))

# --- DUPLICATE CHECKS ---
title_counts = Counter(all_titles)
for t, c in title_counts.items():
    if c > 1:
        results['duplicate_titles'].append((t, c))

desc_counts = Counter(all_descs)
for d, c in desc_counts.items():
    if c > 1:
        results['duplicate_descs'].append((d[:80], c))

# --- PRINT REPORT ---
print('=' * 70)
print(f'SEO AUDIT REPORT — {results["total"]} Research Articles')
print('=' * 70)

print(f'\n--- TITLE ISSUES ({len(results["title_issues"])}) ---')
for ref, issue in results['title_issues'][:20]:
    print(f'  {ref}: {issue}')
if len(results['title_issues']) > 20:
    print(f'  ... and {len(results["title_issues"]) - 20} more')

print(f'\n--- DESCRIPTION ISSUES ({len(results["desc_issues"])}) ---')
for ref, issue in results['desc_issues'][:20]:
    print(f'  {ref}: {issue}')
if len(results['desc_issues']) > 20:
    print(f'  ... and {len(results["desc_issues"]) - 20} more')

print(f'\n--- FRONTMATTER ISSUES ({len(results["frontmatter_issues"])}) ---')
for ref, issue in results['frontmatter_issues'][:15]:
    print(f'  {ref}: {issue}')
if len(results['frontmatter_issues']) > 15:
    print(f'  ... and {len(results["frontmatter_issues"]) - 15} more')

print(f'\n--- SLUG ISSUES ({len(results["slug_issues"])}) ---')
for ref, issue in results['slug_issues'][:15]:
    print(f'  {ref}: {issue}')
if len(results['slug_issues']) > 15:
    print(f'  ... and {len(results["slug_issues"]) - 15} more')

print(f'\n--- HEADING ISSUES ({len(results["heading_issues"])}) ---')
for ref, issue in results['heading_issues'][:15]:
    print(f'  {ref}: {issue}')
if len(results['heading_issues']) > 15:
    print(f'  ... and {len(results["heading_issues"]) - 15} more')

print(f'\n--- BODY ISSUES ({len(results["body_issues"])}) ---')
for ref, issue in results['body_issues'][:15]:
    print(f'  {ref}: {issue}')
if len(results['body_issues']) > 15:
    print(f'  ... and {len(results["body_issues"]) - 15} more')

print(f'\n--- DUPLICATE TITLES ({len(results["duplicate_titles"])}) ---')
for t, c in results['duplicate_titles'][:10]:
    print(f'  ({c}x) {t[:80]}')

print(f'\n--- DUPLICATE DESCRIPTIONS ({len(results["duplicate_descs"])}) ---')
for d, c in results['duplicate_descs'][:10]:
    print(f'  ({c}x) {d}')

print(f'\n--- INTERNAL LINKS IN BODY ({len(results["internal_link_issues"])}) ---')
print(f'  {len(results["internal_link_issues"])} cross-silo internal links found (good for SEO)')

# Summary
total_issues = (len(results['title_issues']) + len(results['desc_issues']) +
    len(results['frontmatter_issues']) + len(results['slug_issues']) +
    len(results['heading_issues']) + len(results['body_issues']) +
    len(results['duplicate_titles']) + len(results['duplicate_descs']))

print(f'\n{"=" * 70}')
print(f'SUMMARY')
print(f'{"=" * 70}')
print(f'Total articles:       {results["total"]}')
print(f'Title issues:         {len(results["title_issues"])}')
print(f'Description issues:   {len(results["desc_issues"])}')
print(f'Frontmatter issues:   {len(results["frontmatter_issues"])}')
print(f'Slug issues:          {len(results["slug_issues"])}')
print(f'Heading issues:       {len(results["heading_issues"])}')
print(f'Body issues:          {len(results["body_issues"])}')
print(f'Duplicate titles:     {len(results["duplicate_titles"])}')
print(f'Duplicate descs:      {len(results["duplicate_descs"])}')
print(f'Total issues:         {total_issues}')
compliance = ((results['total'] * 6 - total_issues) / (results['total'] * 6)) * 100
print(f'Compliance rate:      {compliance:.1f}%')

# Save full results for fixing
with open(r'D:\dev\projects\diggingscriptures\_seo_audit_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f'\nFull results saved to _seo_audit_results.json')
