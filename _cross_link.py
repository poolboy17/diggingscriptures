"""
Cross-silo internal linking: pilgrimage <-> research
Strategy:
1. Read all pilgrimage articles (hubs, places, routes, stories, context)
2. Read all research articles
3. Find topic overlaps via keyword matching
4. Inject contextual links into article bodies
"""
import os, re, json

CONTENT = r'D:\dev\projects\diggingscriptures\src\content'

def read_frontmatter(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    m = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    if not m:
        return None, text
    fm_text = m.group(1)
    title = ''
    desc = ''
    for line in fm_text.split('\n'):
        if line.startswith('title:'):
            title = line.split(':', 1)[1].strip().strip('"').strip("'")
        if line.startswith('description:'):
            desc = line.split(':', 1)[1].strip().strip('"').strip("'")
    return {'title': title, 'description': desc}, text

# Collect pilgrimage articles
pilgrimage_types = ['hubs', 'places', 'routes', 'stories', 'context']
pilgrimage = []
for ptype in pilgrimage_types:
    pdir = os.path.join(CONTENT, ptype)
    if not os.path.isdir(pdir):
        continue
    for f in os.listdir(pdir):
        if not f.endswith('.md'):
            continue
        fp = os.path.join(pdir, f)
        fm, _ = read_frontmatter(fp)
        if fm:
            slug = f.replace('.md', '')
            pilgrimage.append({
                'type': ptype,
                'slug': slug,
                'title': fm['title'],
                'url': f'/{ptype}/{slug}',
                'path': fp,
            })

# Collect research articles
research = []
rdir = os.path.join(CONTENT, 'research')
for cat in os.listdir(rdir):
    catdir = os.path.join(rdir, cat)
    if not os.path.isdir(catdir):
        continue
    for f in os.listdir(catdir):
        if not f.endswith('.md'):
            continue
        fp = os.path.join(catdir, f)
        fm, _ = read_frontmatter(fp)
        if fm:
            slug = f.replace('.md', '')
            research.append({
                'category': cat,
                'slug': slug,
                'title': fm['title'],
                'url': f'/research/{cat}/{slug}',
                'path': fp,
            })

print(f'Pilgrimage articles: {len(pilgrimage)}')
print(f'Research articles: {len(research)}')

# Define topic bridges — keywords that connect pilgrimage to research
# Each bridge: keyword -> list of research slugs that match
# Strategy: for each pilgrimage article, find research articles with overlapping topics

# Key location/topic terms to match on
location_terms = {
    'jerusalem': 'jerusalem',
    'temple mount': 'temple',
    'dead sea': 'dead-sea',
    'jericho': 'jericho',
    'bethlehem': 'bethlehem',
    'nazareth': 'nazareth',
    'galilee': 'galilee',
    'jordan': 'jordan',
    'qumran': 'qumran',
    'masada': 'masada',
    'hebron': 'hebron',
    'samaria': 'samaria',
    'capernaum': 'capernaum',
    'dead sea scrolls': 'dead-sea-scroll',
    'old testament': 'old-testament',
    'new testament': 'new-testament',
    'archaeology': 'archaeolog',
    'excavation': 'excavat',
    'artifact': 'artifact',
    'bible': 'bibl',
    'scripture': 'scripture',
    'pilgrimage': 'pilgrim',
    'temple': 'temple',
    'ancient': 'ancient',
    'israel': 'israel',
    'holy land': 'holy-land',
}

# For each pilgrimage article, find top 3 most relevant research articles
links_to_add = {}  # pilgrimage_path -> [(research_url, research_title)]
research_backlinks = {}  # research_path -> [(pilgrimage_url, pilgrimage_title)]

for p in pilgrimage:
    # Read body text
    with open(p['path'], 'r', encoding='utf-8') as f:
        body = f.read().lower()
    
    scores = []
    for r in research:
        score = 0
        r_slug_lower = r['slug'].lower()
        r_title_lower = r['title'].lower()
        
        # Check if research title terms appear in pilgrimage body
        for word in r_title_lower.split():
            if len(word) > 4 and word in body:
                score += 1
        
        # Check location overlap
        for term, pattern in location_terms.items():
            if pattern in body and pattern in r_slug_lower:
                score += 3
        
        if score > 3:
            scores.append((score, r))
    
    # Top 2 research links per pilgrimage article
    scores.sort(key=lambda x: -x[0])
    top = scores[:2]
    if top:
        links_to_add[p['path']] = [(s[1]['url'], s[1]['title'], p['url'], p['title']) for s in top]

# For each research article, find top 1 most relevant pilgrimage article  
for r in research:
    with open(r['path'], 'r', encoding='utf-8') as f:
        body = f.read().lower()
    
    scores = []
    for p in pilgrimage:
        score = 0
        p_slug_lower = p['slug'].lower()
        p_title_lower = p['title'].lower()
        
        for word in p_title_lower.split():
            if len(word) > 4 and word in body:
                score += 1
        
        for term, pattern in location_terms.items():
            if pattern in body and pattern in p_slug_lower:
                score += 3
        
        if score > 3:
            scores.append((score, p))
    
    scores.sort(key=lambda x: -x[0])
    top = scores[:1]
    if top:
        research_backlinks[r['path']] = [(s[1]['url'], s[1]['title']) for s in top]

print(f'\nPilgrimage articles getting research links: {len(links_to_add)}')
print(f'Research articles getting pilgrimage links: {len(research_backlinks)}')

# Now inject the links
# For pilgrimage: add a "Related Research" section before the last heading or at the end
# For research: add a "Related Pilgrimage Guide" section at the end

changes = 0

for path, links in links_to_add.items():
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Skip if already has cross-links
    if 'Related Research' in content:
        continue
    
    # Build link section
    link_md = '\n\n---\n\n### Related Research\n\n'
    for url, title, _, _ in links:
        link_md += f'- [{title}]({url})\n'
    
    # Add before final --- or at end
    content = content.rstrip() + link_md
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    changes += 1

for path, links in research_backlinks.items():
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'Related Pilgrimage' in content:
        continue
    
    link_md = '\n\n---\n\n### Related Pilgrimage Guides\n\n'
    for url, title in links:
        link_md += f'- [{title}]({url})\n'
    
    content = content.rstrip() + link_md
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    changes += 1

print(f'\nTotal files modified with cross-links: {changes}')
