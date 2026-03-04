import re
f = open('src/layouts/ResearchLayout.astro','r',encoding='utf-8').read()
print('Per-page og:image' if 'ogImage' in f or 'og:image' in f else 'NO per-page og:image')
print('Article schema' if 'Article' in f and 'schema' in f.lower() else 'NO Article schema')
print('breadcrumbs prop' if 'breadcrumbs' in f else 'NO breadcrumbs')
# Also check BaseLayout for dynamic OG
b = open('src/layouts/BaseLayout.astro','r',encoding='utf-8').read()
print('OG image is STATIC default' if 'og-default' in b and 'image' not in [p.strip() for p in re.findall(r'interface Props.*?}', b, re.DOTALL)[0].split(';')] else 'OG image may be dynamic')
