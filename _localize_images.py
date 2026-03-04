"""
Download all external research images to public/images/research/
and update frontmatter to use local CDN paths.
"""
import os, re, sys, time, urllib.request, hashlib
sys.stdout.reconfigure(encoding='utf-8')

CONTENT = r'D:\dev\projects\diggingscriptures\src\content\research'
IMG_DIR = r'D:\dev\projects\diggingscriptures\public\images\research'

# Create output dirs
for cat in ['artifacts','biblical-archaeology','excavations','faith','scripture']:
    os.makedirs(os.path.join(IMG_DIR, cat), exist_ok=True)

def download_image(url, dest):
    """Download image, return True on success."""
    if os.path.exists(dest):
        return True
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (DiggingScriptures/1.0)'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            if len(data) < 1000:
                print(f'  WARN: tiny file ({len(data)} bytes)')
                return False
            with open(dest, 'wb') as f:
                f.write(data)
            return True
    except Exception as e:
        print(f'  DL ERROR: {e}')
        return False

def get_ext_from_url(url):
    """Guess extension from URL."""
    url_lower = url.lower()
    if '.png' in url_lower:
        return '.png'
    if '.webp' in url_lower:
        return '.webp'
    return '.jpg'  # Default for Pixabay/Unsplash

def main():
    total = 0
    downloaded = 0
    skipped = 0
    failed = 0

    for cat in sorted(os.listdir(CONTENT)):
        catdir = os.path.join(CONTENT, cat)
        if not os.path.isdir(catdir):
            continue

        files = sorted([f for f in os.listdir(catdir) if f.endswith('.md')])
        print(f'\n=== {cat} ({len(files)} articles) ===')

        for fname in files:
            filepath = os.path.join(catdir, fname)
            slug = fname[:-3]
            total += 1

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract current image URL from frontmatter
            fm_match = re.match(r'^(---\s*\n)(.*?)(\n---\s*\n)', content, re.DOTALL)
            if not fm_match:
                skipped += 1
                continue

            fm = fm_match.group(2)
            img_match = re.search(r'image:\s*"([^"]+)"', fm)
            if not img_match:
                skipped += 1
                continue

            img_url = img_match.group(1)

            # Skip if already local
            if img_url.startswith('/images/'):
                skipped += 1
                continue

            # Download
            ext = get_ext_from_url(img_url)
            local_name = f'{slug}{ext}'
            local_path = os.path.join(IMG_DIR, cat, local_name)
            local_url = f'/images/research/{cat}/{local_name}'

            ok = download_image(img_url, local_path)
            if not ok:
                failed += 1
                print(f'  FAIL: {slug}')
                continue

            # Update frontmatter with local path
            new_fm = fm.replace(f'image: "{img_url}"', f'image: "{local_url}"')
            new_content = fm_match.group(1) + new_fm + fm_match.group(3) + content[fm_match.end():]

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)

            downloaded += 1
            if downloaded % 25 == 0:
                print(f'  Progress: {downloaded} downloaded...')
            time.sleep(0.15)  # Be nice to servers

    print(f'\n{"=" * 60}')
    print(f'DONE: {downloaded} downloaded, {skipped} skipped, {failed} failed')
    print(f'Total articles: {total}')
    print(f'{"=" * 60}')

if __name__ == '__main__':
    main()
