"""
Image fetcher for 680 research articles.
Dual-source: Pixabay (primary, 100 req/min) + Unsplash (fallback, 50 req/hr).
Strategy: Pool-based — fetch category image pools, distribute across articles.
Reads API keys from .env file.
"""
import os, re, json, time, urllib.request, urllib.parse, sys, hashlib
sys.stdout.reconfigure(encoding='utf-8')

# Load keys from .env
def load_env():
    env = {}
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env

ENV = load_env()
PIXABAY_KEY = ENV['PIXABAY_API_KEY']
UNSPLASH_KEY = ENV['UNSPLASH_API_KEY']
CONTENT = os.path.join(os.path.dirname(__file__), 'src', 'content', 'research')

# Category-specific search queries (10 per category x 3 results = 30 images per pool)
CATEGORY_QUERIES = {
    'biblical-archaeology': [
        'biblical archaeology excavation',
        'ancient ruins middle east',
        'archaeological dig site desert',
        'ancient stone ruins israel',
        'archaeology tools excavation site',
        'ancient temple ruins columns',
        'desert archaeological landscape',
        'ancient pottery shards',
        'middle east ancient landscape',
        'jerusalem ancient stone walls',
    ],
    'scripture': [
        'ancient manuscript scroll parchment',
        'old hebrew text writing',
        'ancient bible manuscript pages',
        'dead sea scrolls cave',
        'old testament manuscript',
        'ancient writing tablet clay',
        'historic religious text book',
        'ancient library scrolls shelves',
        'ancient calligraphy ink',
        'old leather bound book pages',
    ],
    'excavations': [
        'archaeological excavation trench',
        'ancient city ruins aerial view',
        'dig site ancient walls foundation',
        'archaeological fieldwork tools',
        'ancient ruins columns pillars',
        'excavation site workers digging',
        'ancient fortress ruins landscape',
        'ruins desert valley',
        'ancient stone wall remains',
        'archaeological site holy land',
    ],
    'artifacts': [
        'ancient pottery ceramic vase',
        'museum ancient artifacts display',
        'ancient coins collection',
        'ancient seal stamp cylinder',
        'archaeological artifacts glass case',
        'ancient bronze statue figurine',
        'ancient jewelry gold necklace',
        'stone inscription carved',
        'ancient clay tablet cuneiform',
        'museum biblical archaeology',
    ],
    'faith': [
        'ancient church interior mosaic',
        'jerusalem western wall',
        'ancient synagogue mosaic floor',
        'sacred religious site pilgrimage',
        'ancient temple steps worship',
        'religious ceremony candles',
        'historic cathedral stained glass',
        'ancient religious fresco painting',
        'pilgrimage holy land path',
        'ancient mosaic religious art',
    ],
}

def search_pixabay(query, per_page=3):
    """Search Pixabay API. Returns list of {url, alt, credit}."""
    params = urllib.parse.urlencode({
        'key': PIXABAY_KEY,
        'q': query,
        'image_type': 'photo',
        'orientation': 'horizontal',
        'min_width': 1080,
        'per_page': per_page,
        'safesearch': 'true',
    })
    url = f'https://pixabay.com/api/?{params}'
    results = []
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode())
            for hit in data.get('hits', []):
                results.append({
                    'url': hit['largeImageURL'],
                    'alt': hit.get('tags', query),
                    'credit': f"Image by {hit.get('user', 'Unknown')} on Pixabay",
                })
    except Exception as e:
        print(f'  PIXABAY ERROR: {e}')
    return results

def search_unsplash(query, per_page=3):
    """Search Unsplash API. Returns list of {url, alt, credit}."""
    params = urllib.parse.urlencode({
        'query': query, 'per_page': per_page,
        'orientation': 'landscape', 'content_filter': 'high',
        'client_id': UNSPLASH_KEY,
    })
    url = f'https://api.unsplash.com/search/photos?{params}'
    req = urllib.request.Request(url, headers={'Accept-Version': 'v1'})
    results = []
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            for photo in data['results']:
                results.append({
                    'url': photo['urls']['regular'],
                    'alt': photo['alt_description'] or query,
                    'credit': f"Photo by {photo['user']['name']} on Unsplash",
                })
    except Exception as e:
        print(f'  UNSPLASH ERROR: {e}')
    return results

def build_image_pools():
    """Fetch image pools for each category using Pixabay primary + Unsplash fallback."""
    pools = {}
    api_calls = 0
    for cat, queries in CATEGORY_QUERIES.items():
        print(f'\n=== Building pool: {cat} ({len(queries)} queries) ===')
        pool = []
        seen_urls = set()

        for query in queries:
            # Try Pixabay first (generous rate limit)
            results = search_pixabay(query, per_page=3)
            api_calls += 1

            if not results:
                # Fallback to Unsplash
                results = search_unsplash(query, per_page=2)
                api_calls += 1
                time.sleep(1.5)  # Unsplash rate limit caution

            for r in results:
                if r['url'] not in seen_urls:
                    seen_urls.add(r['url'])
                    pool.append(r)

            time.sleep(0.7)  # Be nice to APIs
            print(f'  {query}: +{len(results)} images (pool: {len(pool)})')

        pools[cat] = pool
        print(f'  Pool total: {len(pool)} unique images')

    print(f'\nTotal API calls: {api_calls}')
    return pools

def distribute_images(pools):
    """Assign images from pools to articles, round-robin within category."""
    updated = 0
    skipped = 0

    for cat in os.listdir(CONTENT):
        catdir = os.path.join(CONTENT, cat)
        if not os.path.isdir(catdir):
            continue

        pool = pools.get(cat, [])
        if not pool:
            print(f'\n  WARNING: No images for {cat}')
            continue

        files = sorted([f for f in os.listdir(catdir) if f.endswith('.md')])
        print(f'\n=== Distributing: {cat} ({len(files)} articles, {len(pool)} images) ===')

        for i, fname in enumerate(files):
            filepath = os.path.join(catdir, fname)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Skip if already has image
            fm_match = re.match(r'^(---\s*\n)(.*?)(\n---\s*\n)', content, re.DOTALL)
            if not fm_match:
                continue
            if 'image:' in fm_match.group(2):
                skipped += 1
                continue

            # Round-robin assign from pool
            img = pool[i % len(pool)]

            # Escape quotes in alt/credit
            alt = img['alt'].replace('"', "'")
            credit = img['credit'].replace('"', "'")

            block = f'\nimage: "{img["url"]}"'
            block += f'\nimageAlt: "{alt}"'
            block += f'\nimageCredit: "{credit}"'

            new_content = fm_match.group(1) + fm_match.group(2) + block + fm_match.group(3) + content[fm_match.end():]

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated += 1

    return updated, skipped


def main():
    """Main pipeline: build image pools, distribute to articles."""
    print('=' * 60)
    print('DiggingScriptures Research Image Fetcher')
    print('Pixabay (primary) + Unsplash (fallback)')
    print('=' * 60)

    # Count articles first
    total = 0
    for cat in os.listdir(CONTENT):
        catdir = os.path.join(CONTENT, cat)
        if os.path.isdir(catdir):
            count = len([f for f in os.listdir(catdir) if f.endswith('.md')])
            print(f'  {cat}: {count} articles')
            total += count
    print(f'  Total: {total} articles\n')

    # Phase 1: Build image pools from APIs
    print('PHASE 1: Building image pools...')
    pools = build_image_pools()

    # Save pools to JSON for debugging/reuse
    pools_file = os.path.join(os.path.dirname(__file__), '_image_pools.json')
    serializable = {}
    for cat, imgs in pools.items():
        serializable[cat] = imgs
    with open(pools_file, 'w', encoding='utf-8') as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)
    print(f'\nPools saved to {pools_file}')

    # Phase 2: Distribute images to articles
    print('\nPHASE 2: Distributing images to articles...')
    updated, skipped = distribute_images(pools)

    print(f'\n{"=" * 60}')
    print(f'DONE: {updated} articles updated, {skipped} already had images')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()
