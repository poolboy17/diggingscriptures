"""Remove the 18 spam articles with Lorem Ipsum content."""
import os

CONTENT = r'D:\dev\projects\diggingscriptures\src\content\research'
spam_slugs = [
    'carry-on-luggage', 'cybersecurity', 'emerging-artists',
    'family-friendly-escapes', 'hidden-gems-europe', 'latest-laptops',
    'mixing-patterns', 'noise-canceling-headphones', 'playlist-perfection',
    'revamp-your-space', 'road-trip-europe', 'seasonal-styling',
    'smart-home-revolution', 'smart-wearables', 'solo-travel-diaries',
    'sustainable-living', 'the-age-of-ai', 'vinyl-revival',
]

removed = 0
for cat in os.listdir(CONTENT):
    catdir = os.path.join(CONTENT, cat)
    if not os.path.isdir(catdir):
        continue
    for f in os.listdir(catdir):
        slug = f.replace('.md', '')
        if slug in spam_slugs:
            filepath = os.path.join(catdir, f)
            os.remove(filepath)
            print(f'  DELETED: {cat}/{slug}')
            removed += 1

print(f'\nRemoved {removed} spam articles')
