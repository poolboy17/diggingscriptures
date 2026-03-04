"""Download images for ONE category. Usage: python _dl_cat.py <category>"""
import os, re, sys, time, urllib.request
sys.stdout.reconfigure(encoding='utf-8')

CAT = sys.argv[1] if len(sys.argv) > 1 else 'artifacts'
CONTENT = os.path.join(r'D:\dev\projects\diggingscriptures\src\content\research', CAT)
IMG_DIR = os.path.join(r'D:\dev\projects\diggingscriptures\public\images\research', CAT)
os.makedirs(IMG_DIR, exist_ok=True)

def dl(url, dest):
    if os.path.exists(dest):
        return True
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = r.read()
        if len(d) < 1000:
            return False
        with open(dest, 'wb') as f:
            f.write(d)
        return True
    except Exception as e:
        print(f'  ERR: {e}')
        return False

ok = 0
fail = 0
skip = 0
files = sorted([f for f in os.listdir(CONTENT) if f.endswith('.md')])
print(f'{CAT}: {len(files)} articles')

for fname in files:
    fp = os.path.join(CONTENT, fname)
    slug = fname[:-3]
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    m = re.match(r'^(---\s*\n)(.*?)(\n---\s*\n)', content, re.DOTALL)
    if not m:
        skip += 1
        continue
    fm = m.group(2)
    im = re.search(r'image:\s*"([^"]+)"', fm)
    if not im:
        skip += 1
        continue
    url = im.group(1)
    if url.startswith('/images/'):
        skip += 1
        continue
    ext = '.jpg'
    local_name = f'{slug}{ext}'
    local_path = os.path.join(IMG_DIR, local_name)
    local_url = f'/images/research/{CAT}/{local_name}'

    if dl(url, local_path):
        new_fm = fm.replace(f'image: "{url}"', f'image: "{local_url}"')
        new_c = m.group(1) + new_fm + m.group(3) + content[m.end():]
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(new_c)
        ok += 1
    else:
        fail += 1
        print(f'  FAIL: {slug}')
    time.sleep(0.1)

print(f'DONE {CAT}: {ok} downloaded, {skip} skipped, {fail} failed')
