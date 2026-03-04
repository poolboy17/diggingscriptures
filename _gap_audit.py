"""Gap analysis audit for DiggingScriptures"""
import os, re, json, glob
from collections import Counter, defaultdict

ROOT = r"D:\dev\projects\diggingscriptures"
SRC = os.path.join(ROOT, "src")
CONTENT = os.path.join(SRC, "content")
PAGES = os.path.join(SRC, "pages")
PUBLIC = os.path.join(ROOT, "public")

gaps = []

# ── 1. CHECK FOR MISSING PAGES ──
print("=" * 60)
print("1. MISSING PAGES & FILES")
print("=" * 60)

# Custom 404
if not os.path.exists(os.path.join(PAGES, "404.astro")):
    gaps.append(("CRITICAL", "No custom 404.astro page — using default Netlify 404"))
    print("  ❌ No custom 404 page")

# About page
if not os.path.exists(os.path.join(PAGES, "about.astro")):
    gaps.append(("HIGH", "No /about page — E-E-A-T signal missing"))
    print("  ❌ No /about page")

# Search
has_search = any(os.path.exists(os.path.join(PAGES, f)) for f in ["search.astro", "search/index.astro"])
if not has_search:
    gaps.append(("MEDIUM", "No search functionality for 735+ articles"))
    print("  ❌ No search page")

# Sitemap
if not os.path.exists(os.path.join(ROOT, "dist", "sitemap-index.xml")):
    print("  ⚠️ No dist/sitemap-index.xml (maybe not built)")
else:
    print("  ✅ Sitemap exists")

# OG image
og_img = os.path.join(PUBLIC, "images", "og-default.jpg")
if not os.path.exists(og_img):
    gaps.append(("HIGH", "Missing og-default.jpg — OG meta references it"))
    print("  ❌ Missing /images/og-default.jpg")
else:
    print("  ✅ og-default.jpg exists")

# favicon
if not os.path.exists(os.path.join(PUBLIC, "favicon.svg")):
    gaps.append(("MEDIUM", "Missing favicon"))
    print("  ❌ Missing favicon")
else:
    print("  ✅ favicon.svg exists")

# _redirects or netlify.toml
has_redirects = os.path.exists(os.path.join(PUBLIC, "_redirects")) or os.path.exists(os.path.join(ROOT, "netlify.toml"))
if not has_redirects:
    gaps.append(("HIGH", "No _redirects file or netlify.toml — 301 redirects from WordPress migration may be missing"))
    print("  ❌ No _redirects or netlify.toml for 301s")

print()

# ── 2. CONTENT ANALYSIS ──
print("=" * 60)
print("2. CONTENT ANALYSIS")
print("=" * 60)

# Check research articles
research_dir = os.path.join(CONTENT, "research")
research_files = glob.glob(os.path.join(research_dir, "**", "*.md"), recursive=True)
print(f"  Research articles: {len(research_files)}")

# Sample frontmatter analysis
missing_desc = 0
missing_img = 0
short_content = 0
no_internal_links = 0
total_words = 0

for fpath in research_files:
    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    
    # Check frontmatter
    fm_match = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        if "description:" not in fm or 'description: ""' in fm:
            missing_desc += 1
        if "image:" not in fm or 'image: ""' in fm:
            missing_img += 1
    
    # Check body content
    body = re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.DOTALL)
    words = len(body.split())
    total_words += words
    if words < 300:
        short_content += 1
    
    # Check internal links
    internal_links = re.findall(r'\[.*?\]\(/[^)]+\)', body)
    if len(internal_links) == 0:
        no_internal_links += 1

print(f"  Missing descriptions: {missing_desc}")
print(f"  Missing images: {missing_img}")
print(f"  Short content (<300 words): {short_content}")
print(f"  No internal links: {no_internal_links}")
print(f"  Avg word count: {total_words // max(len(research_files), 1)}")

if no_internal_links > 0:
    gaps.append(("HIGH", f"{no_internal_links} research articles have ZERO internal links — orphaned content"))
if short_content > 0:
    gaps.append(("MEDIUM", f"{short_content} research articles under 300 words — thin content risk"))

# Check pilgrimage content
for ctype in ["places", "routes", "stories", "context", "hubs"]:
    cdir = os.path.join(CONTENT, ctype)
    if os.path.isdir(cdir):
        files = glob.glob(os.path.join(cdir, "**", "*.md"), recursive=True) + glob.glob(os.path.join(cdir, "**", "*.mdx"), recursive=True)
        print(f"  {ctype}: {len(files)} articles")
    else:
        print(f"  {ctype}: directory not found")

print()

# ── 3. NAVIGATION & LINKING ──
print("=" * 60)
print("3. NAVIGATION & LINKING GAPS")
print("=" * 60)

# Check header nav — does it link to /research?
header_path = os.path.join(SRC, "components", "Header.astro")
with open(header_path, "r", encoding="utf-8") as f:
    header_content = f.read()

if "/research" not in header_content:
    gaps.append(("CRITICAL", "Header nav does NOT link to /research — 680 articles unreachable from main nav"))
    print("  ❌ /research NOT in header navigation")
else:
    print("  ✅ /research in header nav")

# Check footer links
footer_path = os.path.join(SRC, "components", "Footer.astro")
with open(footer_path, "r", encoding="utf-8") as f:
    footer_content = f.read()

if "/research" not in footer_content:
    gaps.append(("HIGH", "Footer does NOT link to /research"))
    print("  ❌ /research NOT in footer")
else:
    print("  ✅ /research in footer")

print()

# ── 4. SEO ELEMENTS CHECK ──
print("=" * 60)
print("4. SEO ELEMENTS")
print("=" * 60)

# Check BaseLayout for key meta tags
base_path = os.path.join(SRC, "layouts", "BaseLayout.astro")
with open(base_path, "r", encoding="utf-8") as f:
    base_content = f.read()

checks = {
    "viewport meta": "viewport" in base_content,
    "canonical URL": "canonical" in base_content,
    "og:title": "og:title" in base_content,
    "og:description": "og:description" in base_content,
    "og:image": "og:image" in base_content,
    "twitter:card": "twitter:card" in base_content,
    "JSON-LD schema": "application/ld+json" in base_content,
    "sitemap link": "sitemap" in base_content,
    "robots.txt": os.path.exists(os.path.join(PUBLIC, "robots.txt")),
    "hreflang": "hreflang" in base_content,
    "preload fonts": "preload" in base_content,
}

for name, exists in checks.items():
    status = "✅" if exists else "❌"
    print(f"  {status} {name}")
    if not exists and name not in ["hreflang"]:  # hreflang optional for English-only
        gaps.append(("LOW", f"Missing {name}"))

# Check for Google Analytics / tracking
has_analytics = "gtag" in base_content or "analytics" in base_content.lower() or "google-analytics" in base_content
if not has_analytics:
    gaps.append(("HIGH", "No Google Analytics or tracking — can't measure traffic"))
    print("  ❌ No analytics/tracking code")

# Check for Google Search Console verification
has_gsc = "google-site-verification" in base_content
if not has_gsc:
    gaps.append(("HIGH", "No Google Search Console verification meta tag"))
    print("  ❌ No Google Search Console verification")

print()

# ── 5. PERFORMANCE ──
print("=" * 60)
print("5. PERFORMANCE & OPTIMIZATION")
print("=" * 60)

# Check image sizes
img_dir = os.path.join(PUBLIC, "images", "research")
if os.path.isdir(img_dir):
    total_img_size = 0
    img_count = 0
    for root_d, dirs, files in os.walk(img_dir):
        for fname in files:
            fpath = os.path.join(root_d, fname)
            total_img_size += os.path.getsize(fpath)
            img_count += 1
    print(f"  Research images: {img_count} files, {total_img_size/1024/1024:.1f}MB total")
    if total_img_size / 1024 / 1024 > 200:
        gaps.append(("MEDIUM", f"Research images total {total_img_size/1024/1024:.0f}MB — consider WebP conversion"))

# Check for WebP usage
webp_count = len(glob.glob(os.path.join(PUBLIC, "**", "*.webp"), recursive=True))
jpg_count = len(glob.glob(os.path.join(PUBLIC, "**", "*.jpg"), recursive=True))
png_count = len(glob.glob(os.path.join(PUBLIC, "**", "*.png"), recursive=True))
print(f"  Image formats: {jpg_count} JPG, {png_count} PNG, {webp_count} WebP")
if webp_count == 0 and (jpg_count + png_count) > 50:
    gaps.append(("MEDIUM", "No WebP images — Netlify Image CDN may handle this, but source WebP would be better"))

# Check for CSS/JS bundles
dist_dir = os.path.join(ROOT, "dist")
if os.path.isdir(dist_dir):
    html_files = glob.glob(os.path.join(dist_dir, "**", "*.html"), recursive=True)
    print(f"  Built HTML pages: {len(html_files)}")

print()

# ── 6. E-E-A-T & TRUST SIGNALS ──
print("=" * 60)
print("6. E-E-A-T & TRUST SIGNALS")
print("=" * 60)

eeat_checks = {
    "About page": os.path.exists(os.path.join(PAGES, "about.astro")),
    "Contact page": os.path.exists(os.path.join(PAGES, "contact.astro")),
    "Privacy policy": os.path.exists(os.path.join(PAGES, "privacy.astro")),
    "Terms of use": os.path.exists(os.path.join(PAGES, "terms.astro")),
    "Affiliate disclaimer": os.path.exists(os.path.join(PAGES, "affiliate-disclaimer.astro")),
    "Author bios": any("author" in f.lower() for f in os.listdir(os.path.join(SRC, "components")) if f.endswith(".astro")),
}

for name, exists in eeat_checks.items():
    status = "✅" if exists else "❌"
    print(f"  {status} {name}")
    if not exists:
        if name == "About page":
            gaps.append(("HIGH", "No About page — critical E-E-A-T gap for YMYL-adjacent content"))
        elif name == "Author bios":
            gaps.append(("HIGH", "No author bio components — E-E-A-T requires demonstrating expertise"))

print()

# ── 7. CONTENT STRUCTURE ──
print("=" * 60)
print("7. CONTENT GAPS & MISSING FEATURES")
print("=" * 60)

# Check for breadcrumbs on research pages
research_layout = os.path.join(SRC, "layouts", "ResearchLayout.astro")
with open(research_layout, "r", encoding="utf-8") as f:
    rl_content = f.read()

if "breadcrumbs" not in rl_content:
    gaps.append(("MEDIUM", "Research pages have NO breadcrumb navigation — hurts SEO and UX"))
    print("  ❌ No breadcrumbs on research pages")

# Check for related articles
if "related" not in rl_content.lower():
    gaps.append(("HIGH", "Research pages have NO related articles section — missed internal linking opportunity"))
    print("  ❌ No related articles on research pages")

# Check for TOC
if "toc" not in rl_content.lower() and "table-of-contents" not in rl_content.lower():
    gaps.append(("MEDIUM", "Research pages have NO table of contents — long articles need navigation"))
    print("  ❌ No table of contents on research pages")

# Check for reading time
if "reading" not in rl_content.lower() and "read-time" not in rl_content.lower():
    gaps.append(("LOW", "No reading time estimate on articles"))
    print("  ❌ No reading time on research pages")

# Check for social sharing
if "share" not in rl_content.lower() and "twitter" not in rl_content.lower():
    gaps.append(("LOW", "No social sharing buttons on articles"))
    print("  ❌ No social sharing on research pages")

# Check for email signup / newsletter
has_newsletter = False
for root_d, dirs, files in os.walk(SRC):
    for f in files:
        if "newsletter" in f.lower() or "subscribe" in f.lower() or "email" in f.lower():
            has_newsletter = True
            break
if not has_newsletter:
    gaps.append(("HIGH", "No email signup/newsletter — no way to capture returning visitors"))
    print("  ❌ No newsletter/email signup")

# Check for pagination on listing pages
research_cat_page = os.path.join(PAGES, "research", "[category]", "index.astro")
if os.path.exists(research_cat_page):
    with open(research_cat_page, "r", encoding="utf-8") as f:
        cat_content = f.read()
    if "paginate" not in cat_content.lower() and "page" not in cat_content.lower():
        gaps.append(("HIGH", "Category pages list ALL articles — no pagination for 100+ article categories"))
        print("  ❌ No pagination on category listing pages")

print()

# ── SUMMARY ──
print("=" * 60)
print("GAP ANALYSIS SUMMARY")
print("=" * 60)

by_severity = defaultdict(list)
for sev, desc in gaps:
    by_severity[sev].append(desc)

for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
    items = by_severity.get(sev, [])
    if items:
        print(f"\n  [{sev}] ({len(items)} issues)")
        for item in items:
            print(f"    • {item}")

print(f"\n  TOTAL GAPS: {len(gaps)}")
print(f"    Critical: {len(by_severity.get('CRITICAL', []))}")
print(f"    High:     {len(by_severity.get('HIGH', []))}")
print(f"    Medium:   {len(by_severity.get('MEDIUM', []))}")
print(f"    Low:      {len(by_severity.get('LOW', []))}")
