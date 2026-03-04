"""
Fix all SEO issues found in the audit:
1. Replace Lorem Ipsum descriptions with real ones generated from body text
2. Convert H1s in body to H2s
3. Fix duplicate title
4. Fix encoded slug
"""
import os, re, json, shutil

CONTENT = r'D:\dev\projects\diggingscriptures\src\content\research'
fixes = {'lorem': 0, 'h1': 0, 'title': 0, 'slug': 0}

def extract_first_sentence(body, max_len=155):
    """Extract a meaningful description from body text."""
    # Remove markdown formatting
    clean = re.sub(r'#{1,6}\s+', '', body)
    clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
    clean = re.sub(r'[*_`]', '', clean)
    clean = re.sub(r'\n+', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    # Remove Related Pilgrimage/Research sections
    clean = re.sub(r'---\s*$', '', clean).strip()

    # Get first 2-3 sentences
    sentences = re.split(r'(?<=[.!?])\s+', clean)
    desc = ''
    for s in sentences:
        s = s.strip()
        if not s or len(s) < 20:
            continue
        if len(desc) + len(s) + 1 <= max_len:
            desc = (desc + ' ' + s).strip() if desc else s
        else:
            break
    if len(desc) < 50 and sentences:
        # Just truncate first sentence
        desc = sentences[0][:max_len-3].rsplit(' ', 1)[0] + '...'
    return desc[:160]

for cat in os.listdir(CONTENT):
    catdir = os.path.join(CONTENT, cat)
    if not os.path.isdir(catdir):
        continue
    for f in os.listdir(catdir):
        if not f.endswith('.md'):
            continue
        filepath = os.path.join(catdir, f)
        slug = f.replace('.md', '')
        ref = f'{cat}/{slug}'
        modified = False

        with open(filepath, 'r', encoding='utf-8') as fh:
            raw = fh.read()

        fm_match = re.match(r'^---\n(.*?)\n---\n(.*)', raw, re.DOTALL)
        if not fm_match:
            continue
        fm_text = fm_match.group(1)
        body = fm_match.group(2)

        # --- FIX 1: Lorem Ipsum descriptions ---
        if 'lorem ipsum' in fm_text.lower():
            new_desc = extract_first_sentence(body)
            if new_desc:
                fm_text = re.sub(
                    r'description:\s*["\'].*?["\']',
                    f'description: "{new_desc}"',
                    fm_text
                )
                fixes['lorem'] += 1
                modified = True
                print(f'  LOREM FIX: {ref} -> {new_desc[:60]}...')

        # --- FIX 2: H1s in body -> H2s ---
        h1s = re.findall(r'^# .+$', body, re.MULTILINE)
        if h1s:
            body = re.sub(r'^# (.+)$', r'## \1', body, flags=re.MULTILINE)
            fixes['h1'] += len(h1s)
            modified = True
            print(f'  H1 FIX: {ref} -> converted {len(h1s)} H1(s) to H2')

        if modified:
            with open(filepath, 'w', encoding='utf-8') as fh:
                fh.write(f'---\n{fm_text}\n---\n{body}')

# --- FIX 3: Encoded slug ---
encoded_path = os.path.join(CONTENT, 'artifacts',
    'where-you-can-view-high%e2%80%91res-original-manuscripts.md')
clean_path = os.path.join(CONTENT, 'artifacts',
    'where-you-can-view-high-res-original-manuscripts.md')
if os.path.exists(encoded_path):
    shutil.move(encoded_path, clean_path)
    fixes['slug'] += 1
    print(f'  SLUG FIX: renamed encoded slug')

# --- FIX 4: Duplicate title ---
# Find the two articles with duplicate title
dup_title = 'unveiling the secrets: the role of biblical archaeologists in'
dup_files = []
for cat in os.listdir(CONTENT):
    catdir = os.path.join(CONTENT, cat)
    if not os.path.isdir(catdir):
        continue
    for f in os.listdir(catdir):
        if not f.endswith('.md'):
            continue
        filepath = os.path.join(catdir, f)
        with open(filepath, 'r', encoding='utf-8') as fh:
            content = fh.read()
        fm_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if fm_match:
            for line in fm_match.group(1).split('\n'):
                if line.startswith('title:'):
                    title = line.split(':', 1)[1].strip().strip('"').strip("'").lower()
                    if dup_title in title:
                        dup_files.append((f'{cat}/{f}', filepath, title))

if len(dup_files) == 2:
    # Differentiate the second one by adding context from its body
    second = dup_files[1]
    with open(second[1], 'r', encoding='utf-8') as fh:
        content = fh.read()
    fm_match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        body = fm_match.group(2)
        # Find a distinguishing keyword from body
        h2s = re.findall(r'^## (.+)$', body, re.MULTILINE)
        suffix = ''
        if h2s:
            # Use first H2 topic
            first_h2 = h2s[0].strip()
            words = first_h2.split()[:3]
            suffix = ' '.join(words)

        old_title_line = [l for l in fm.split('\n') if l.startswith('title:')][0]
        old_title = old_title_line.split(':', 1)[1].strip().strip('"').strip("'")
        new_title = old_title
        if 'Unearthing' not in old_title:
            new_title = old_title.replace('Unveiling', 'Unearthing')
        else:
            new_title = old_title + ' Today'

        fm = fm.replace(old_title_line, f'title: "{new_title}"')
        with open(second[1], 'w', encoding='utf-8') as fh:
            fh.write(f'---\n{fm}\n---\n{body}')
        fixes['title'] += 1
        print(f'  TITLE FIX: {second[0]} -> {new_title}')

print(f'\n=== FIXES APPLIED ===')
print(f'Lorem descriptions fixed: {fixes["lorem"]}')
print(f'H1 headings converted:   {fixes["h1"]}')
print(f'Duplicate titles fixed:   {fixes["title"]}')
print(f'Encoded slugs fixed:      {fixes["slug"]}')
print(f'Total fixes:              {sum(fixes.values())}')
