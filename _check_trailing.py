import re
with open(r"D:\dev\projects\diggingscriptures\dist\sitemap-0.xml", "r", encoding="utf-8") as f:
    content = f.read()
urls = re.findall(r'<loc>(.*?)</loc>', content)
trailing = [u for u in urls if u.endswith('/') and u != 'https://diggingscriptures.com/']
print(f"Total URLs: {len(urls)}")
print(f"Homepage: https://diggingscriptures.com/ -> {'present' if 'https://diggingscriptures.com/' in urls else 'missing'}")
print(f"URLs with trailing slash (excluding homepage): {len(trailing)}")
if trailing:
    for u in trailing[:10]:
        print(f"  {u}")
