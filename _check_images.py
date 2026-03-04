"""Check image status across all research articles."""
import os, re

CONTENT = r'D:\dev\projects\diggingscriptures\src\content\research'
stats = {'total': 0, 'with_fm_image': 0, 'no_fm_image': 0, 'body_images': 0, 'external_images': 0, 'broken_refs': []}

for cat in os.listdir(CONTENT):
    catdir = os.path.join(CONTENT, cat)
    if not os.path.isdir(catdir):
        continue
    for f in os.listdir(catdir):
        if not f.endswith('.md'):
            continue
        stats['total'] += 1
        filepath = os.path.join(catdir, f)
        ref = f'{cat}/{f.replace(".md","")}'

        with open(filepath, 'r', encoding='utf-8') as fh:
            raw = fh.read()

        fm_match = re.match(r'^---\n(.*?)\n---\n(.*)', raw, re.DOTALL)
        if not fm_match:
            continue
        fm = fm_match.group(1)
        body = fm_match.group(2)

        # Check frontmatter image field
        has_image = False
        for line in fm.split('\n'):
            if line.startswith('image:'):
                val = line.split(':', 1)[1].strip().strip('"').strip("'")
                if val:
                    has_image = True
                    # Check if it's a valid path
                    if val.startswith('http'):
                        stats['external_images'] += 1
                    elif val.startswith('/'):
                        img_path = os.path.join(r'D:\dev\projects\diggingscriptures\public', val.lstrip('/'))
                        if not os.path.exists(img_path):
                            stats['broken_refs'].append((ref, f'FM image missing: {val}'))

        if has_image:
            stats['with_fm_image'] += 1
        else:
            stats['no_fm_image'] += 1

        # Check body for image references
        md_images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', body)
        html_images = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', body)
        all_imgs = [(alt, src) for alt, src in md_images] + [('', src) for src in html_images]

        for alt, src in all_imgs:
            stats['body_images'] += 1
            if src.startswith('http'):
                stats['external_images'] += 1

print(f'=== IMAGE AUDIT: {stats["total"]} articles ===')
print(f'Articles with frontmatter image:    {stats["with_fm_image"]}')
print(f'Articles WITHOUT frontmatter image: {stats["no_fm_image"]}')
print(f'Body images found:                  {stats["body_images"]}')
print(f'External image references:          {stats["external_images"]}')
print(f'Broken local image refs:            {len(stats["broken_refs"])}')

if stats['broken_refs']:
    print(f'\n--- BROKEN IMAGE REFS ---')
    for ref, issue in stats['broken_refs'][:20]:
        print(f'  {ref}: {issue}')

# Also check what image files exist in public/images
img_dir = r'D:\dev\projects\diggingscriptures\public\images'
if os.path.exists(img_dir):
    img_files = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg','.jpeg','.png','.webp','.svg'))]
    print(f'\nImages in public/images/: {len(img_files)}')
else:
    print(f'\nNo public/images/ directory found')
