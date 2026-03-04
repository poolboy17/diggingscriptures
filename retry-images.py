import sys, json, time, os, re, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')

KEY = "sTukSVa8nHEj1MJDiJCb-WHA7xSx0ju-rAoZp70xlGw"
BASE = r"D:\dev\projects\diggingscriptures\src\content"

retries = {
    "places/hebron-cave-patriarchs": "hebron israel ancient holy site",
    "routes/abraham-path": "desert trail middle east hiking",
    "routes/kumano-kodo": "japan ancient forest trail torii",
    "stories/legend-of-saint-james": "compostela cathedral spain medieval",
}

for key, query in retries.items():
    ctype, slug = key.split("/")
    fpath = os.path.join(BASE, ctype, f"{slug}.md")
    print(f"[{key}] query='{query}'")
    params = urllib.parse.urlencode({
        "query": query, "per_page": 1,
        "orientation": "landscape", "client_id": KEY
    })
    url = f"https://api.unsplash.com/search/photos?{params}"
    resp = urllib.request.urlopen(url)
    data = json.loads(resp.read())
    if not data["results"]:
        print("  FAIL again"); continue
    photo = data["results"][0]
    img = photo["urls"]["regular"]
    alt = photo["alt_description"] or query
    credit = f"Photo by {photo['user']['name']} on Unsplash"
    # Update frontmatter
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.match(r"^(---\s*\n)(.*?)(\n---\s*\n)", content, re.DOTALL)
    if m and "image:" not in m.group(2):
        block = f'\nimage: "{img}"\nimageAlt: "{alt}"\nimageCredit: "{credit}"'
        new = m.group(1) + m.group(2) + block + m.group(3) + content[m.end():]
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"  OK: {credit}")
    else:
        print("  SKIP")
    time.sleep(1.5)