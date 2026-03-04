import os, re

cats = ['biblical-archaeology','scripture','excavations','artifacts','faith']
research = 'src/content/research'

for cat in cats:
    cat_dir = os.path.join(research, cat)
    titles = []
    for f in sorted(os.listdir(cat_dir)):
        if not f.endswith('.md'): continue
        with open(os.path.join(cat_dir, f), 'r', encoding='utf-8') as fh:
            raw = fh.read(500)
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', raw, re.MULTILINE)
        if m:
            titles.append(m.group(1))
    print(f"\n=== {cat} ({len(titles)} articles) ===")
    for t in titles[:20]:
        print(f"  {t[:80]}")
    if len(titles) > 20:
        print(f"  ... +{len(titles)-20} more")
