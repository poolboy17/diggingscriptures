"""Check sitemap coverage against built HTML pages"""
import os, re, glob

ROOT = r"D:\dev\projects\diggingscriptures"
DIST = os.path.join(ROOT, "dist")

# 1. Get all HTML pages from dist
html_files = glob.glob(os.path.join(DIST, "**", "index.html"), recursive=True)
built_urls = set()
for f in html_files:
    rel = os.path.relpath(f, DIST).replace("\\", "/")
    # index.html -> /
    # research/biblical-archaeology/slug/index.html -> /research/biblical-archaeology/slug
    url = "/" + rel.replace("/index.html", "")
    if url == "/.":
        url = "/"
    built_urls.add(url)

print(f"Built HTML pages: {len(built_urls)}")

# 2. Parse sitemap
sitemap_dir = DIST
sitemap_urls = set()

# Check for sitemap-index
idx_path = os.path.join(sitemap_dir, "sitemap-index.xml")
if os.path.exists(idx_path):
    with open(idx_path, "r", encoding="utf-8") as f:
        idx_content = f.read()
    # Find all sitemap files referenced
    sitemap_files = re.findall(r'<loc>(.*?)</loc>', idx_content)
    print(f"Sitemap index references: {len(sitemap_files)} sitemaps")
    
    for sf_url in sitemap_files:
        # Extract filename from URL
        fname = sf_url.split("/")[-1]
        sf_path = os.path.join(sitemap_dir, fname)
        if os.path.exists(sf_path):
            with open(sf_path, "r", encoding="utf-8") as f:
                content = f.read()
            urls = re.findall(r'<loc>(.*?)</loc>', content)
            for u in urls:
                # Strip domain
                path = u.replace("https://diggingscriptures.com", "")
                if not path:
                    path = "/"
                sitemap_urls.add(path)
        else:
            print(f"  WARNING: {fname} not found on disk")
else:
    # Try single sitemap.xml
    sm_path = os.path.join(sitemap_dir, "sitemap-0.xml")
    if os.path.exists(sm_path):
        with open(sm_path, "r", encoding="utf-8") as f:
            content = f.read()
        urls = re.findall(r'<loc>(.*?)</loc>', content)
        for u in urls:
            path = u.replace("https://diggingscriptures.com", "")
            if not path:
                path = "/"
            sitemap_urls.add(path)

print(f"Sitemap URLs: {len(sitemap_urls)}")

# 3. Compare
in_build_not_sitemap = built_urls - sitemap_urls
in_sitemap_not_build = sitemap_urls - built_urls

print(f"\n{'='*60}")
print(f"COVERAGE ANALYSIS")
print(f"{'='*60}")
print(f"  Pages built:       {len(built_urls)}")
print(f"  Pages in sitemap:  {len(sitemap_urls)}")
print(f"  Match rate:        {len(built_urls & sitemap_urls)}/{len(built_urls)} ({100*len(built_urls & sitemap_urls)/max(len(built_urls),1):.1f}%)")

if in_build_not_sitemap:
    print(f"\n  MISSING FROM SITEMAP ({len(in_build_not_sitemap)}):")
    for url in sorted(in_build_not_sitemap)[:30]:
        print(f"    - {url}")
    if len(in_build_not_sitemap) > 30:
        print(f"    ... and {len(in_build_not_sitemap)-30} more")

if in_sitemap_not_build:
    print(f"\n  IN SITEMAP BUT NO PAGE ({len(in_sitemap_not_build)}):")
    for url in sorted(in_sitemap_not_build)[:20]:
        print(f"    - {url}")

if not in_build_not_sitemap and not in_sitemap_not_build:
    print("\n  ✅ PERFECT MATCH — every built page is in the sitemap")
