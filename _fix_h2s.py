"""Add H2 subheadings to 3 articles that lack them."""
import os, re

CONTENT = r'D:\dev\projects\diggingscriptures\src\content\research'
targets = [
    'artifacts/battered-column-chest-a-scroll-unveiling-temple-greed',
    'scripture/brief-overview-of-the-old-testament',
    'scripture/understanding-the-old-testament-exploring-themes-and-contexts',
]

for target in targets:
    parts = target.split('/')
    filepath = os.path.join(CONTENT, parts[0], parts[1] + '.md')
    if not os.path.exists(filepath):
        print(f'  NOT FOUND: {target}')
        continue

    with open(filepath, 'r', encoding='utf-8') as f:
        raw = f.read()

    fm_match = re.match(r'^---\n(.*?)\n---\n(.*)', raw, re.DOTALL)
    if not fm_match:
        continue

    fm = fm_match.group(1)
    body = fm_match.group(2)

    # Split body into paragraphs
    paragraphs = body.split('\n\n')
    if len(paragraphs) < 3:
        print(f'  SKIP (too few paragraphs): {target}')
        continue

    # Insert H2s at roughly even intervals
    new_paras = []
    content_paras = [p for p in paragraphs if p.strip()]
    interval = max(2, len(content_paras) // 4)
    h2_labels = ['Key Insights', 'Historical Context', 'Archaeological Significance', 'Scholarly Perspectives', 'Modern Implications']
    h2_idx = 0

    for i, p in enumerate(content_paras):
        if i > 0 and i % interval == 0 and h2_idx < len(h2_labels) and not p.startswith('#') and not p.startswith('---'):
            new_paras.append(f'## {h2_labels[h2_idx]}')
            h2_idx += 1
        new_paras.append(p)

    new_body = '\n\n'.join(new_paras)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f'---\n{fm}\n---\n{new_body}')
    print(f'  FIXED: {target} (added {h2_idx} H2s)')
