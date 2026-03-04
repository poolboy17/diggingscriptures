"""Scan affiliate sites to count articles and extract categories."""
import os, json, re

sites = {
    "cursedtours": {
        "path": r"D:\dev\projects\cursedtours\src\data\articles",
        "format": "json",
    },
    "devour-destinations": {
        "path": r"D:\dev\projects\devour-destinations\src\content\posts",
        "format": "md",
    },
    "protrainerprep": {
        "path": r"D:\dev\projects\protrainerprep\src\data\post",
        "format": "mdx",
    },
}

for site, cfg in sites.items():
    path = cfg["path"]
    fmt = cfg["format"]
    cats = {}
    count = 0
    for f in sorted(os.listdir(path)):
        if not f.endswith(f".{fmt}"):
            continue
        count += 1
        fp = os.path.join(path, f)
        with open(fp, "r", encoding="utf-8") as fh:
            raw = fh.read()
        if fmt == "json":
            try:
                data = json.loads(raw)
                for c in data.get("categories", []):
                    slug = c.get("slug", "unknown")
                    cats[slug] = cats.get(slug, 0) + 1
            except: pass
        else:
            # MD/MDX frontmatter
            m = re.search(r'^category:\s*["\']?(.+?)["\']?\s*$', raw, re.MULTILINE)
            if not m:
                m = re.search(r'^categorySlug:\s*["\']?(.+?)["\']?\s*$', raw, re.MULTILINE)
            if m:
                cat = m.group(1).strip().strip('"').strip("'")
                cats[cat] = cats.get(cat, 0) + 1
            else:
                cats["_uncategorized"] = cats.get("_uncategorized", 0) + 1

    print(f"\n{'='*60}")
    print(f"  {site}: {count} articles")
    print(f"{'='*60}")
    for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:40s} {n:4d}")
