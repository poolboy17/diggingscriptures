"""Deep sample - full content of 3 posts to assess quality."""
import re
import html
import xml.etree.ElementTree as ET

XML_PATH = r"D:\New folder\diggingscriptures.xml"
NS = {
    'wp': 'http://wordpress.org/export/1.2/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
}

print("Loading XML...")
with open(XML_PATH, "r", encoding="utf-8", errors="replace") as f:
    raw = f.read()
raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
root = ET.fromstring(raw)
channel = root.find('channel')

targets = [
    'the-ultimate-beginners-guide-to-biblical-archaeology',
    'exploring-ancient-jerusalem-pilgrim-routes-unearthed',
    'replicas-in-exile-the-quest-for-the-real-ark-of-the-covenant',
]

for item in channel.findall('item'):
    sl = item.find('wp:post_name', NS)
    slug = sl.text if sl is not None and sl.text else ''
    if slug not in targets:
        continue
    
    title = item.find('title').text or ''
    ce = item.find('content:encoded', NS)
    content = ce.text if ce is not None and ce.text else ''
    
    # Strip HTML but keep paragraph breaks
    text = re.sub(r'</(p|h[1-6]|li|div|blockquote)>', '\n\n', content)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    
    words = len(text.split())
    
    print("=" * 80)
    print(f"TITLE: {title}")
    print(f"SLUG:  {slug}")
    print(f"WORDS: {words}")
    print("-" * 80)
    # Print first 2000 chars to assess quality
    print(text[:2000])
    print("\n[... truncated ...]\n")
