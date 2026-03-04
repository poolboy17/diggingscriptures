"""
Optimize all research images:
- Resize to max 1280px wide (preserve aspect ratio)
- Compress JPEG to quality 80
- Track actual dimensions for frontmatter update
"""
import os, sys, json
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image

IMG_DIR = r'D:\dev\projects\diggingscriptures\public\images\research'
MAX_W = 1280
QUALITY = 80

optimized = 0
already_ok = 0
total_saved = 0
dimensions = {}  # {relative_path: (w, h)}

for cat in sorted(os.listdir(IMG_DIR)):
    catdir = os.path.join(IMG_DIR, cat)
    if not os.path.isdir(catdir):
        continue
    print(f'\n=== {cat} ===')

    cat_saved = 0
    for fname in sorted(os.listdir(catdir)):
        if not fname.endswith(('.jpg', '.png', '.webp')):
            continue
        fpath = os.path.join(catdir, fname)
        orig_size = os.path.getsize(fpath)
        rel_path = f'/images/research/{cat}/{fname}'

        try:
            img = Image.open(fpath)
            w, h = img.size

            needs_resize = w > MAX_W
            if needs_resize:
                ratio = MAX_W / w
                new_h = int(h * ratio)
                img = img.resize((MAX_W, new_h), Image.LANCZOS)
                w, h = MAX_W, new_h

            # Convert to RGB if needed (for JPEG save)
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')

            # Save optimized
            img.save(fpath, 'JPEG', quality=QUALITY, optimize=True)
            new_size = os.path.getsize(fpath)
            saved = orig_size - new_size
            total_saved += saved
            cat_saved += saved

            dimensions[rel_path] = (w, h)

            if needs_resize:
                optimized += 1
            else:
                already_ok += 1

        except Exception as e:
            print(f'  ERROR {fname}: {e}')
            dimensions[rel_path] = (1280, 853)  # safe fallback

    print(f'  Saved: {cat_saved // 1024}KB')

# Save dimensions map for frontmatter update
dims_file = os.path.join(os.path.dirname(IMG_DIR), '_image_dimensions.json')
with open(dims_file, 'w') as f:
    json.dump(dimensions, f, indent=2)

print(f'\n{"=" * 60}')
print(f'Optimized: {optimized} resized, {already_ok} already OK')
print(f'Total saved: {total_saved // 1024 // 1024}MB')
print(f'Dimensions saved to _image_dimensions.json')
print(f'{"=" * 60}')
