import os, re
sitemap_dir = r'D:\dev\projects\diggingscriptures\dist'
count = 0
for f in os.listdir(sitemap_dir):
    if f.startswith('sitemap') and f.endswith('.xml'):
        path = os.path.join(sitemap_dir, f)
        with open(path, 'r', encoding='utf-8') as fh:
            content = fh.read()
        urls = re.findall(r'<loc>(.*?)</loc>', content)
        print(f'{f}: {len(urls)} URLs')
        count += len(urls)
        # Show a few research URLs
        research = [u for u in urls if '/research/' in u]
        if research:
            print(f'  Research URLs: {len(research)}')
            for u in research[:3]:
                print(f'    {u}')
print(f'\nTotal URLs in sitemap: {count}')
