"""
Full QC Audit for DiggingScriptures
====================================
Audits the built dist/ folder + source content for:
1. Frontmatter completeness (all required fields present)
2. Image references (do local images exist? are Unsplash URLs valid?)
3. Internal link integrity (no broken links)
4. Meta tags in built HTML (title, description, OG tags)
5. Word count minimums
6. Heading structure (no duplicate H1s)
7. Empty pages / missing content
"""

import os, re, sys, io, json, yaml, glob
from pathlib import Path
from html.parser import HTMLParser
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(BASE, 'dist')
CONTENT = os.path.join(BASE, 'src', 'content')
PUBLIC = os.path.join(BASE, 'public')

CONTENT_TYPES = ['hubs', 'places', 'routes', 'stories', 'context']
issues = defaultdict(list)  # severity -> list of (file, message)

# ============================================================
# 1. FRONTMATTER AUDIT
# ============================================================
def audit_frontmatter():
    print("\n=== 1. FRONTMATTER AUDIT ===")
    required = {
        'hubs': ['title', 'description', 'draft'],
        'places': ['title', 'description', 'region', 'country', 'faithTraditions', 'parentHub', 'draft'],
        'routes': ['title', 'description', 'region', 'countries', 'faithTraditions', 'parentHub', 'draft'],
        'stories': ['title', 'description', 'storyType', 'faithTraditions', 'draft'],
        'context': ['title', 'description', 'contextType', 'faithTraditions', 'draft'],
    }
    count = 0
    for ctype in CONTENT_TYPES:
        cdir = os.path.join(CONTENT, ctype)
        if not os.path.isdir(cdir):
            continue
        for fname in sorted(os.listdir(cdir)):
            if not fname.endswith('.md'):
                continue
            count += 1
            fpath = os.path.join(cdir, fname)
            with open(fpath, encoding='utf-8') as f:
                raw = f.read()
            m = re.match(r'^---\s*\n(.*?)\n---', raw, re.DOTALL)
            if not m:
                issues['BLOCKER'].append((fname, 'No frontmatter found'))
                continue
            fm = yaml.safe_load(m.group(1)) or {}
            for field in required.get(ctype, []):
                if field not in fm:
                    issues['BLOCKER'].append((fname, f'Missing required field: {field}'))
            # Check draft status
            if fm.get('draft') is True:
                issues['WARN'].append((fname, 'Still in draft mode'))
            # Check description length
            desc = fm.get('description', '')
            if len(desc) < 50:
                issues['WARN'].append((fname, f'Description too short: {len(desc)}c'))
            if len(desc) > 160:
                issues['WARN'].append((fname, f'Description too long: {len(desc)}c'))
            # Check title length
            title = fm.get('title', '')
            if len(title) > 65:
                issues['WARN'].append((fname, f'Title too long for SEO: {len(title)}c'))
            # Check lastUpdated
            if 'lastUpdated' not in fm:
                issues['WARN'].append((fname, 'Missing lastUpdated'))
    print(f"  Scanned {count} articles")
