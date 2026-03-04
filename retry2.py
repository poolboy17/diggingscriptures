import sys, json, re, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')
KEY = "sTukSVa8nHEj1MJDiJCb-WHA7xSx0ju-rAoZp70xlGw"
fpath = r"D:\dev\projects\diggingscriptures\src\content\places\hebron-cave-patriarchs.md"
query = "ancient stone tomb holy land"
params = urllib.parse.urlencode({"query": query, "per_page": 1, "orientation": "landscape", "client_id": KEY})
resp = urllib.request.urlopen(f"https://api.unsplash.com/search/photos?{params}")
data = json.loads(resp.read())
if data["results"]:
    p = data["results"][0]
    img, alt, credit = p["urls"]["regular"], p["alt_description"] or query, f"Photo by {p['user']['name']} on Unsplash"
    with open(fpath, "r", encoding="utf-8") as f: content = f.read()
    m = re.match(r"^(---\s*\n)(.*?)(\n---\s*\n)", content, re.DOTALL)
    if m and "image:" not in m.group(2):
        block = f'\nimage: "{img}"\nimageAlt: "{alt}"\nimageCredit: "{credit}"'
        new = m.group(1) + m.group(2) + block + m.group(3) + content[m.end():]
        with open(fpath, "w", encoding="utf-8") as f: f.write(new)
        print(f"OK: {credit}")
    else: print("SKIP")
else: print("FAIL")