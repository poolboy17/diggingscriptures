import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
CONTENT = r'D:\dev\projects\diggingscriptures\src\content\research'
has_img = 0
no_img = 0
for cat in os.listdir(CONTENT):
    catdir = os.path.join(CONTENT, cat)
    if not os.path.isdir(catdir):
        continue
    files = [f for f in os.listdir(catdir) if f.endswith('.md')]
    cat_img = 0
    for f in files:
        with open(os.path.join(catdir, f), 'r', encoding='utf-8') as fh:
            head = fh.read(2000)
        if 'image:' in head.split('---')[1] if '---' in head else '':
            cat_img += 1
            has_img += 1
        else:
            no_img += 1
            print(f'  MISSING: {cat}/{f}')
    print(f'{cat}: {cat_img}/{len(files)} have images')
print(f'\nTotal: {has_img} with images, {no_img} without')
