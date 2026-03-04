import os, sys
sys.stdout.reconfigure(encoding='utf-8')
base = r'D:\dev\projects\diggingscriptures\public\images\research'
total = 0
for cat in sorted(os.listdir(base)):
    d = os.path.join(base, cat)
    if os.path.isdir(d):
        imgs = [f for f in os.listdir(d) if f.endswith(('.jpg','.png','.webp'))]
        total += len(imgs)
        # Sample file size
        if imgs:
            sz = os.path.getsize(os.path.join(d, imgs[0]))
            print(f'{cat}: {len(imgs)} images (sample: {sz//1024}KB)')
        else:
            print(f'{cat}: 0 images')
print(f'\nTotal: {total} images on disk')
