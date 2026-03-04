#!/usr/bin/env python3
"""
Unsplash Image Fetcher for DiggingScriptures
Searches Unsplash for relevant images and updates article frontmatter.
"""

import os
import re
import json
import time
import yaml
import urllib.request
import urllib.parse
from pathlib import Path

import sys
sys.stdout.reconfigure(encoding='utf-8')

UNSPLASH_KEY = "sTukSVa8nHEj1MJDiJCb-WHA7xSx0ju-rAoZp70xlGw"
BASE_DIR = r"D:\dev\projects\diggingscriptures"
CONTENT_DIR = os.path.join(BASE_DIR, "src", "content")
API_URL = "https://api.unsplash.com/search/photos"
# Search query mappings — hand-tuned for best Unsplash results
SEARCH_OVERRIDES = {
    # Places
    "jerusalem": "jerusalem old city golden dome",
    "jerusalem-old-city": "jerusalem western wall old city",
    "western-wall": "western wall jerusalem prayer",
    "dome-of-the-rock": "dome of the rock jerusalem",
    "mecca": "mecca kaaba pilgrimage",
    "medina": "medina mosque prophet muhammad",
    "varanasi": "varanasi ganges river ghats",
    "bodh-gaya": "bodh gaya mahabodhi temple",
    "lumbini": "lumbini nepal buddha birthplace",
    "rome-vatican": "vatican st peters basilica rome",
    "santiago-de-compostela": "santiago de compostela cathedral",
    "lourdes": "lourdes grotto france",
    "mount-koya": "mount koya japan temple",
    "safed-kabbalah": "safed israel synagogue",
    "hebron-cave-patriarchs": "hebron cave patriarchs",
    # Routes
    "camino-de-santiago": "camino de santiago pilgrims walking",
    "via-francigena": "via francigena italy pilgrimage path",
    "kumano-kodo": "kumano kodo japan forest trail",
    "shikoku-88-temples": "shikoku pilgrimage japan temple",
    "hajj-route": "hajj pilgrimage mecca crowd",
    "abraham-path": "abraham path middle east trail",
    "kora-mount-kailash": "mount kailash tibet pilgrimage",
    "st-olavs-way": "st olavs way norway pilgrimage",
    # Stories
    "legend-of-saint-james": "santiago apostle cathedral",
    "egeria-first-pilgrim-writer": "ancient manuscript pilgrimage",
    "ibn-battuta-pilgrim-traveler": "medieval islamic travel map",
    "helena-and-the-true-cross": "church holy sepulchre jerusalem",
    "kobo-daishi-shikoku": "shingon buddhist monk japan",
    "rabbi-nachman-journey-to-israel": "jewish prayer jerusalem",
    "xuanzang-buddhist-pilgrim": "silk road buddhist temple",
    "margery-kempe-medieval-pilgrim": "medieval pilgrimage europe cathedral",
    # Context
    "history-of-christian-pilgrimage": "medieval christian pilgrimage",
    "four-sacred-sites-buddhism": "buddhist sacred sites temple",
    "five-pillars-hajj-explained": "hajj pilgrimage kaaba",
    "three-pilgrim-festivals-judaism": "jewish pilgrimage jerusalem temple",
    "pilgrimage-tourism-modern-era": "modern pilgrimage tourism",
    "relics-and-sacred-objects": "religious relics sacred objects",
    # Hubs
    "christian-pilgrimage-traditions": "christian pilgrimage cathedral",
    "faith-based-journeys": "pilgrimage sacred journey path",
    "buddhist-pilgrimage-paths": "buddhist pilgrimage asia temple",
    "jewish-pilgrimage-heritage": "jewish pilgrimage western wall",
    "islamic-pilgrimage-traditions": "islamic pilgrimage mosque",
}


def search_unsplash(query, per_page=1):
    """Search Unsplash API and return first result."""
    params = urllib.parse.urlencode({
        "query": query,
        "per_page": per_page,
        "orientation": "landscape",
        "content_filter": "high",
        "client_id": UNSPLASH_KEY,
    })
    url = f"{API_URL}?{params}"
    req = urllib.request.Request(url, headers={"Accept-Version": "v1"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            if data["results"]:
                photo = data["results"][0]
                # Use regular size (1080w) for hero images
                image_url = photo["urls"]["regular"]
                alt = photo["alt_description"] or query
                credit = f"Photo by {photo['user']['name']} on Unsplash"
                return image_url, alt, credit
    except Exception as e:
        print(f"  ERROR: {e}")
    return None, None, None


def discover_articles():
    """Find all markdown articles across all content types."""
    articles = []
    for ctype in ["hubs", "places", "routes", "stories", "context"]:
        cdir = os.path.join(CONTENT_DIR, ctype)
        if not os.path.isdir(cdir):
            continue
        for fname in os.listdir(cdir):
            if fname.endswith(".md"):
                slug = fname[:-3]
                fpath = os.path.join(cdir, fname)
                articles.append((ctype, slug, fpath))
    return articles


def load_frontmatter(fpath):
    """Extract frontmatter from markdown file."""
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return None, content
    fm_raw = m.group(1)
    try:
        fm = yaml.safe_load(fm_raw)
    except:
        fm = {}
    return fm, content


def update_frontmatter(fpath, image_url, alt, credit):
    """Add image fields to frontmatter of a markdown file."""
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Find the closing --- of frontmatter
    m = re.match(r"^(---\s*\n)(.*?)(\n---\s*\n)", content, re.DOTALL)
    if not m:
        print(f"  SKIP: no frontmatter found")
        return False
    
    fm_raw = m.group(2)
    
    # Check if image already exists
    if "image:" in fm_raw:
        print(f"  SKIP: already has image")
        return False
    
    # Add image fields before the closing ---
    image_block = f'\nimage: "{image_url}"'
    image_block += f'\nimageAlt: "{alt}"'
    image_block += f'\nimageCredit: "{credit}"'
    
    new_content = m.group(1) + fm_raw + image_block + m.group(3) + content[m.end():]
    
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def main():
    """Main pipeline: discover articles, fetch images, update frontmatter."""
    articles = discover_articles()
    print(f"Found {len(articles)} articles\n")
    
    success = 0
    skipped = 0
    failed = 0
    
    for ctype, slug, fpath in articles:
        print(f"[{ctype}/{slug}]")
        
        # Check if already has image
        fm, _ = load_frontmatter(fpath)
        if fm and fm.get("image"):
            print(f"  SKIP: already has image")
            skipped += 1
            continue
        
        # Build search query
        if slug in SEARCH_OVERRIDES:
            query = SEARCH_OVERRIDES[slug]
        else:
            # Fallback: use title if available, else slug
            title = fm.get("title", slug.replace("-", " ")) if fm else slug.replace("-", " ")
            query = f"{title} pilgrimage"
        
        print(f"  Searching: '{query}'")
        image_url, alt, credit = search_unsplash(query)
        
        if image_url:
            updated = update_frontmatter(fpath, image_url, alt, credit)
            if updated:
                print(f"  OK: {credit}")
                success += 1
            else:
                skipped += 1
        else:
            print(f"  FAIL: no results")
            failed += 1
        
        # Rate limit: Unsplash allows 50 req/hr on free tier
        time.sleep(1.5)
    
    print(f"\n{'='*50}")
    print(f"Results: {success} updated, {skipped} skipped, {failed} failed")
    print(f"Total: {len(articles)} articles")


if __name__ == "__main__":
    main()
