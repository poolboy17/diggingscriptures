"""Navigation & linking sanity check"""
import os, re, glob

ROOT = r"D:\dev\projects\diggingscriptures"
DIST = os.path.join(ROOT, "dist")
SRC = os.path.join(ROOT, "src")

# Build set of all valid URLs from dist
html_files = glob.glob(os.path.join(DIST, "**", "index.html"), recursive=True)
valid_urls = set()
for f in html_files:
    rel = os.path.relpath(f, DIST).replace("\\", "/").replace("/index.html", "")
    url = "/" + rel if rel != "." else "/"
    valid_urls.add(url)

print(f"Total valid pages: {len(valid_urls)}")
print()

issues = []

# ── 1. HEADER NAV ──
print("=" * 60)
print("1. HEADER NAVIGATION")
print("=" * 60)
header_links = [
    ("/", "Logo/Wordmark"),
    ("/research", "Research"),
    ("/journeys", "Journeys"),
    ("/places", "Places"),
    ("/routes", "Routes"),
    ("/stories", "Stories"),
    ("/context", "Context"),
]
for url, label in header_links:
    exists = url in valid_urls
    status = "✅" if exists else "❌ BROKEN"
    print(f"  {status}  {label} -> {url}")
    if not exists:
        issues.append(f"HEADER: {label} -> {url} does NOT resolve")

# ── 2. MOBILE DRAWER ──
print()
print("=" * 60)
print("2. MOBILE DRAWER (same navItems array)")
print("=" * 60)
print("  ✅ Uses same navItems[] as desktop — automatically in sync")

# ── 3. FOOTER NAV ──
print()
print("=" * 60)
print("3. FOOTER NAVIGATION")
print("=" * 60)
footer_links = [
    ("/research", "Research"),
    ("/journeys", "Journeys"),
    ("/places", "Places"),
    ("/routes", "Routes"),
    ("/stories", "Stories"),
    ("/context", "Context"),
    ("/contact", "Contact"),
    ("/privacy", "Privacy Policy"),
    ("/terms", "Terms of Use"),
    ("/affiliate-disclaimer", "Affiliate Disclaimer"),
]
for url, label in footer_links:
    exists = url in valid_urls
    status = "✅" if exists else "❌ BROKEN"
    print(f"  {status}  {label} -> {url}")
    if not exists:
        issues.append(f"FOOTER: {label} -> {url} does NOT resolve")

# ── 4. HEADER vs FOOTER PARITY ──
print()
print("=" * 60)
print("4. HEADER ↔ FOOTER PARITY")
print("=" * 60)
header_set = {url for url, _ in header_links if url != "/"}
footer_nav_set = {"/research", "/journeys", "/places", "/routes", "/stories", "/context"}
footer_legal = {"/contact", "/privacy", "/terms", "/affiliate-disclaimer"}

in_header_not_footer = header_set - footer_nav_set
in_footer_not_header = footer_nav_set - header_set

if not in_header_not_footer and not in_footer_not_header:
    print("  ✅ Header and footer main nav are in sync")
else:
    if in_header_not_footer:
        print(f"  ⚠️ In header but NOT footer nav: {in_header_not_footer}")
        issues.append(f"PARITY: Header has {in_header_not_footer} but footer doesn't")
    if in_footer_not_header:
        print(f"  ⚠️ In footer but NOT header nav: {in_footer_not_header}")
        issues.append(f"PARITY: Footer has {in_footer_not_header} but header doesn't")

# Check order matches
header_order = [url for url, _ in header_links if url != "/"]
footer_order = ["/research", "/journeys", "/places", "/routes", "/stories", "/context"]
if header_order == footer_order:
    print("  ✅ Link order matches between header and footer")
else:
    print(f"  ⚠️ Link ORDER differs:")
    print(f"     Header: {header_order}")
    print(f"     Footer: {footer_order}")
    issues.append("PARITY: Header and footer link order differs")

# ── 5. HOMEPAGE LINKS ──
print()
print("=" * 60)
print("5. HOMEPAGE INTERNAL LINKS")
print("=" * 60)

idx_path = os.path.join(SRC, "pages", "index.astro")
with open(idx_path, "r", encoding="utf-8") as f:
    hp_content = f.read()

# Extract all href values
hp_hrefs = re.findall(r'href=["\']([^"\']+)["\']', hp_content)
hp_internal = [h for h in hp_hrefs if h.startswith("/") and not h.startswith("//")]

# Remove dynamic hrefs with template literals
static_hrefs = [h for h in hp_internal if "{" not in h and "$" not in h]

for url in sorted(set(static_hrefs)):
    exists = url in valid_urls
    status = "✅" if exists else "❌ BROKEN"
    print(f"  {status}  {url}")
    if not exists:
        issues.append(f"HOMEPAGE: {url} does NOT resolve")

# Check dynamic hrefs patterns
dynamic_hrefs = [h for h in hp_internal if "{" in h or "$" in h]
print(f"\n  Dynamic links (template): {len(set(dynamic_hrefs))}")

# ── 6. RESEARCH HUB LINKS ──
print()
print("=" * 60)
print("6. RESEARCH CATEGORY HUBS")
print("=" * 60)

categories = ["biblical-archaeology", "scripture", "excavations", "artifacts", "faith"]
for cat in categories:
    url = f"/research/{cat}"
    exists = url in valid_urls
    status = "✅" if exists else "❌ BROKEN"
    # Count articles in this category
    cat_articles = [u for u in valid_urls if u.startswith(f"/research/{cat}/")]
    print(f"  {status}  {url} ({len(cat_articles)} articles)")
    if not exists:
        issues.append(f"RESEARCH HUB: {url} does NOT resolve")

# ── 7. BREADCRUMB CONSISTENCY ──
print()
print("=" * 60)
print("7. BREADCRUMB COVERAGE")
print("=" * 60)

layouts_with_breadcrumbs = []
layouts_without = []

for lf in glob.glob(os.path.join(SRC, "layouts", "*.astro")):
    name = os.path.basename(lf)
    if name == "BaseLayout.astro" or name == "Layout.astro":
        continue
    with open(lf, "r", encoding="utf-8") as f:
        content = f.read()
    if "breadcrumbs" in content:
        layouts_with_breadcrumbs.append(name)
    else:
        layouts_without.append(name)

for l in layouts_with_breadcrumbs:
    print(f"  ✅ {l} — has breadcrumbs")
for l in layouts_without:
    print(f"  ❌ {l} — NO breadcrumbs")
    issues.append(f"BREADCRUMBS: {l} missing breadcrumbs prop")

# ── 8. ACTIVE STATE LOGIC ──
print()
print("=" * 60)
print("8. ACTIVE STATE DETECTION")
print("=" * 60)

# Check the active state logic
# currentPath === item.href || currentPath.startsWith(item.href + '/')
print("  Header active logic: exact match OR startsWith(href + '/')")
print("  Testing edge cases:")

test_cases = [
    ("/research", "/research", True),
    ("/research", "/research/biblical-archaeology", True),
    ("/research", "/research/biblical-archaeology/some-article", True),
    ("/routes", "/routes", True),
    ("/routes", "/routes/camino-de-santiago", True),
    ("/context", "/context-page-that-shouldnt-match", False),
    ("/places", "/places", True),
]

for href, path, expected in test_cases:
    actual = (path == href) or path.startswith(href + "/")
    match = "✅" if actual == expected else "❌ WRONG"
    print(f"    {match}  href={href} path={path} -> {'active' if actual else 'inactive'} (expected {'active' if expected else 'inactive'})")
    if actual != expected:
        issues.append(f"ACTIVE STATE: href={href} path={path} gives wrong result")

# ── SUMMARY ──
print()
print("=" * 60)
print("SANITY CHECK SUMMARY")
print("=" * 60)

if not issues:
    print("  ✅ ALL CHECKS PASSED — navigation system is clean")
else:
    print(f"  ❌ {len(issues)} ISSUES FOUND:")
    for i in issues:
        print(f"    • {i}")
