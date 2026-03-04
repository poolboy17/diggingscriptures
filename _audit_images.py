"""
Audit all research images: dimensions, file size, aspect ratios.
Requires Pillow: pip install Pillow
"""
import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8')

IMG_DIR = r'D:\dev\projects\diggingscriptures\public\images\research'

def get_jpeg_dimensions(filepath):
    """Get JPEG dimensions without Pillow."""
    with open(filepath, 'rb') as f:
        data = f.read()
    # Find SOF markers (0xFFC0 through 0xFFC3)
    i = 0
    while i < len(data) - 1:
        if data[i] == 0xFF:
            marker = data[i+1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                # SOF marker found
                h = struct.unpack('>H', data[i+5:i+7])[0]
                w = struct.unpack('>H', data[i+7:i+9])[0]
                return w, h
            elif marker == 0xD8 or marker == 0xD9:
                i += 2
            elif marker == 0x00:
                i += 1
            else:
                # Skip to next marker
                if i + 3 < len(data):
                    length = struct.unpack('>H', data[i+2:i+4])[0]
                    i += 2 + length
                else:
                    break
        else:
            i += 1
    return None, None

# Stats
sizes = []
widths = []
heights = []
aspect_ratios = {}
too_small = []
too_large = []
broken = []
total = 0

for cat in sorted(os.listdir(IMG_DIR)):
    catdir = os.path.join(IMG_DIR, cat)
    if not os.path.isdir(catdir):
        continue
    for fname in sorted(os.listdir(catdir)):
        if not fname.endswith(('.jpg','.png','.webp')):
            continue
        fpath = os.path.join(catdir, fname)
        fsize = os.path.getsize(fpath)
        total += 1
        sizes.append(fsize)

        w, h = get_jpeg_dimensions(fpath)
        if w and h:
            widths.append(w)
            heights.append(h)
            ratio = round(w/h, 2)
            aspect_ratios[ratio] = aspect_ratios.get(ratio, 0) + 1
            if w < 600:
                too_small.append(f'{cat}/{fname} ({w}x{h})')
            if fsize > 500000:  # >500KB
                too_large.append(f'{cat}/{fname} ({fsize//1024}KB, {w}x{h})')
        else:
            broken.append(f'{cat}/{fname} ({fsize//1024}KB)')

print(f'Total images: {total}')
print(f'\nFile sizes:')
print(f'  Min: {min(sizes)//1024}KB')
print(f'  Max: {max(sizes)//1024}KB')
print(f'  Avg: {sum(sizes)//len(sizes)//1024}KB')
print(f'  Total: {sum(sizes)//1024//1024}MB')

if widths:
    print(f'\nDimensions:')
    print(f'  Width range: {min(widths)}-{max(widths)}px')
    print(f'  Height range: {min(heights)}-{max(heights)}px')
    print(f'  Avg: {sum(widths)//len(widths)}x{sum(heights)//len(heights)}')

print(f'\nAspect ratios (top 5):')
for ratio, count in sorted(aspect_ratios.items(), key=lambda x: -x[1])[:5]:
    print(f'  {ratio}:1 — {count} images')

if too_small:
    print(f'\nToo small (<600px wide): {len(too_small)}')
    for s in too_small[:10]:
        print(f'  {s}')

if too_large:
    print(f'\nOversized (>500KB): {len(too_large)}')
    for s in too_large[:10]:
        print(f'  {s}')
    if len(too_large) > 10:
        print(f'  ... and {len(too_large)-10} more')

if broken:
    print(f'\nCould not read dimensions: {len(broken)}')
    for b in broken[:10]:
        print(f'  {b}')

print(f'\nParsed: {len(widths)}/{total} images')
