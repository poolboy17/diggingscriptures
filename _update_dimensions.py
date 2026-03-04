"""
Add imageWidth/imageHeight to all research article frontmatter
based on actual measured dimensions from _image_dimensions.json.
"""
import os, re, sys, json
sys.stdout.reconfigure(encoding='utf-8')

CONTENT = r'D:\dev\projects\diggingscriptures\src\content\research'
DIMS_FILE = r'D:\dev\projects\diggingscriptures\public\images\_image_dimensions.json'

with open(DIMS_FILE, 'r') as f:
    dims = json.load(f)

updated = 0
skipped = 0

for cat in sorted(os.listdir(CONTENT)):
    catdir = os.path.join(CONTENT, cat)
    if not os.path.isdir(catdir):
        continue

    for fname in sorted(os.listdir(catdir)):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(catdir, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        m = re.match(r'^(---\s*\n)(.*?)(\n---\s*\n)', content, re.DOTALL)
        if not m:
            skipped += 1
            continue

        fm = m.group(2)

        # Skip if already has dimensions
        if 'imageWidth:' in fm:
            skipped += 1
            continue

        # Get image path from frontmatter
        img_match = re.search(r'image:\s*"([^"]+)"', fm)
        if not img_match:
            skipped += 1
            continue

        img_path = img_match.group(1)
        if img_path not in dims:
            skipped += 1
            continue

        w, h = dims[img_path]

        # Add imageWidth/imageHeight after imageCredit line
        dim_block = f'\nimageWidth: {w}\nimageHeight: {h}'

        # Insert after imageCredit if present, otherwise after image line
        if 'imageCredit:' in fm:
            new_fm = re.sub(
                r'(imageCredit:\s*"[^"]*")',
                r'\1' + dim_block,
                fm
            )
        else:
            new_fm = re.sub(
                r'(image:\s*"[^"]*")',
                r'\1' + dim_block,
                fm
            )

        new_content = m.group(1) + new_fm + m.group(3) + content[m.end():]
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        updated += 1

print(f'Updated: {updated}, Skipped: {skipped}')
