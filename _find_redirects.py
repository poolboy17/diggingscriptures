import os, re

old_slugs = [
    'the-ultimate-beginners-guide-to-biblical-archaeology',
    'were-the-new-testament-books-written-in-hebrew',
    'continuity-and-discontinuity-the-relationship-between-the-old-testament-and-the-new-testament',
    'is-the-ethiopian-bible-the-most-accurate',
    'what-is-the-difference-between-the-ethiopian-bible-and-the-bible',
    'how-many-times-has-the-bible-been-changed',
]

base = r'D:\dev\projects\diggingscriptures\src\content\research'
for cat in os.listdir(base):
    cat_path = os.path.join(base, cat)
    if not os.path.isdir(cat_path):
        continue
    for f in os.listdir(cat_path):
        slug = f.replace('.md', '')
        if slug in old_slugs:
            print(f'/{slug}/ -> /research/{cat}/{slug}/')
