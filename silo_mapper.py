#!/usr/bin/env python3
"""
Silo Mapper — Site-Agnostic SEO Pyramid Schema
================================================
Assigns every article a position in the SEO pyramid via frontmatter fields.
Designed to be reusable across any static Markdown content site.

SCHEMA (injected into YAML frontmatter):
  siloTier:     "hub" | "pillar" | "cluster" | "support"
  siloCluster:  cluster slug within category (e.g. "dead-sea-scrolls")
  siloParent:   URL of the direct parent page
  siloPriority: 1-100 (higher = more authoritative within cluster)

TIERS (standard SEO pyramid):
  hub      — category landing pages (/research/biblical-archaeology)
  pillar   — broad comprehensive guides (longest, highest link equity)
  cluster  — subtopic group pages (medium depth)
  support  — individual articles (narrowest focus)

CLUSTERING ALGORITHM:
  1. Extract title n-grams (bigrams + trigrams) from all articles in a category
  2. Group articles by their most distinctive shared n-gram
  3. Merge small clusters (<3 articles) into nearest neighbor
  4. Name clusters by their dominant n-gram
  5. Rank articles within cluster by word count (proxy for depth)

Usage:
  python silo_mapper.py --analyze                    # Show clusters, don't write
  python silo_mapper.py --apply                      # Write frontmatter fields
  python silo_mapper.py --apply --category scripture  # Single category
  python silo_mapper.py --export silo-map.json       # Export map for tooling

Can also be imported: from silo_mapper import classify_article, get_silo_map
"""

import os, sys, re, json, argparse
from collections import defaultdict, Counter
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════
# Site-Agnostic Configuration — Override these per project
# ═══════════════════════════════════════════════════════════════

# Default: DiggingScriptures research articles
CONTENT_DIR = os.path.join(BASE_DIR, "src", "content", "research")
CATEGORIES = ["biblical-archaeology", "scripture", "excavations", "artifacts", "faith"]
HUB_URLS = {
    "biblical-archaeology": "/research/biblical-archaeology",
    "scripture": "/research/scripture",
    "excavations": "/research/excavations",
    "artifacts": "/research/artifacts",
    "faith": "/research/faith",
}

# Clustering tunables
MIN_CLUSTER_SIZE = 3    # clusters smaller than this get merged
MAX_CLUSTERS_PER_CAT = 15  # cap clusters per category for manageable linking
PILLAR_THRESHOLD_WC = 1500  # word count above which a support page may be a pillar
PILLAR_MAX_PER_CLUSTER = 1  # max pillar pages per cluster

# Stop words for n-gram extraction (site-agnostic)
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "was", "are", "be",
    "this", "that", "how", "what", "why", "who", "where", "when",
    "its", "our", "your", "their", "into", "not", "has", "have",
    "you", "we", "they", "can", "do", "does", "did", "will", "would",
    "new", "old", "all", "between", "through", "about", "more",
    "most", "also", "just", "been", "being", "had", "than", "very",
    "some", "other", "each", "which", "much", "many", "may", "up",
}


# ═══════════════════════════════════════════════════════════════
# Frontmatter Parsing (site-agnostic)
# ═══════════════════════════════════════════════════════════════

def parse_md_file(filepath):
    """Parse a Markdown file, return (frontmatter_dict, body, raw)."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()
    if not raw.startswith("---"):
        return {}, raw, raw
    idx = raw.index("---", 3)
    fm_block = raw[4:idx].strip()
    body = raw[idx+3:].lstrip("\n")

    fm = {}
    for line in fm_block.split("\n"):
        m = re.match(r'^(\w[\w\-]*)\s*:\s*(.+)$', line)
        if m:
            key = m.group(1)
            val = m.group(2).strip().strip('"').strip("'")
            fm[key] = val
    return fm, body, raw


def write_silo_fields(filepath, silo_tier, silo_cluster, silo_parent, silo_priority):
    """Inject or update silo fields in a Markdown file's frontmatter."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()
    if not raw.startswith("---"):
        return False

    idx = raw.index("---", 3)
    fm_block = raw[4:idx]
    body_part = raw[idx:]  # includes closing --- and body

    # Remove any existing silo fields
    fm_lines = fm_block.split("\n")
    fm_lines = [l for l in fm_lines if not re.match(r'^silo(Tier|Cluster|Parent|Priority)\s*:', l)]

    # Append new silo fields before closing ---
    # Find the last non-empty line
    while fm_lines and not fm_lines[-1].strip():
        fm_lines.pop()

    fm_lines.append(f'siloTier: "{silo_tier}"')
    fm_lines.append(f'siloCluster: "{silo_cluster}"')
    fm_lines.append(f'siloParent: "{silo_parent}"')
    fm_lines.append(f'siloPriority: {silo_priority}')
    fm_lines.append("")  # trailing newline before ---

    new_raw = "---\n" + "\n".join(fm_lines) + body_part
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_raw)
    return True


# ═══════════════════════════════════════════════════════════════
# Text Extraction & N-gram Generation
# ═══════════════════════════════════════════════════════════════

def clean_title(title):
    """Normalize title for keyword extraction."""
    # Remove common prefixes/suffixes
    title = re.sub(r'\b(unveiling|exploring|discovering|uncovering|unearthing)\b', '', title, flags=re.I)
    title = re.sub(r'\b(a deep dive into|a journey through|a closer look at)\b', '', title, flags=re.I)
    title = re.sub(r'\b(the secrets of|the mysteries of|the significance of)\b', '', title, flags=re.I)
    title = re.sub(r'\b(in biblical archaeology|in ancient|from biblical)\b', '', title, flags=re.I)
    return title.strip()

def extract_tokens(text, min_len=3):
    """Extract meaningful lowercase tokens from text."""
    words = re.findall(r'[a-z]+', text.lower())
    return [w for w in words if len(w) >= min_len and w not in STOP_WORDS]


def make_ngrams(tokens, n=2):
    """Generate n-grams from a token list."""
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


def get_article_signature(title, body_preview=""):
    """Extract a set of distinctive n-grams from title + body start."""
    cleaned = clean_title(title)
    tokens = extract_tokens(cleaned + " " + body_preview[:300])
    bigrams = make_ngrams(tokens, 2)
    trigrams = make_ngrams(tokens, 3)
    return set(bigrams + trigrams)


# ═══════════════════════════════════════════════════════════════
# Clustering Engine (site-agnostic)
# ═══════════════════════════════════════════════════════════════

def load_articles(category_filter=None):
    """Load all articles with metadata. Returns dict keyed by slug."""
    articles = {}
    cats = [category_filter] if category_filter else CATEGORIES
    for cat in cats:
        cat_dir = os.path.join(CONTENT_DIR, cat)
        if not os.path.isdir(cat_dir):
            continue
        for fname in sorted(os.listdir(cat_dir)):
            if not fname.endswith(".md"):
                continue
            slug = fname[:-3]
            filepath = os.path.join(cat_dir, fname)
            fm, body, raw = parse_md_file(filepath)
            title = fm.get("title", slug.replace("-", " ").title())
            wc = len(body.split())
            url = f"/research/{cat}/{slug}"

            signature = get_article_signature(title, body)

            articles[slug] = {
                "filepath": filepath,
                "title": title,
                "category": cat,
                "url": url,
                "word_count": wc,
                "signature": signature,
                "tokens": extract_tokens(clean_title(title)),
            }
    return articles


def cluster_category(articles, cat):
    """
    Cluster articles within a single category using n-gram co-occurrence.
    Returns {cluster_name: [slug, ...]}
    """
    cat_articles = {s: a for s, a in articles.items() if a["category"] == cat}
    if not cat_articles:
        return {}

    # Count all bigrams across titles in this category
    bigram_counter = Counter()
    slug_bigrams = {}
    for slug, art in cat_articles.items():
        bigrams = make_ngrams(art["tokens"], 2)
        slug_bigrams[slug] = set(bigrams)
        for bg in bigrams:
            bigram_counter[bg] += 1

    # Filter bigrams: need at least MIN_CLUSTER_SIZE articles sharing them
    # but not so common they're meaningless (cap at 60% of category)
    max_freq = int(len(cat_articles) * 0.6)
    viable_bigrams = {bg: cnt for bg, cnt in bigram_counter.items()
                      if MIN_CLUSTER_SIZE <= cnt <= max_freq}

    # Assign each article to its most distinctive viable bigram
    assignments = {}
    for slug, art in cat_articles.items():
        best_bg = None
        best_score = -1
        for bg in slug_bigrams.get(slug, set()):
            if bg in viable_bigrams:
                # Prefer rarer bigrams (more distinctive)
                score = 1.0 / viable_bigrams[bg]
                if score > best_score:
                    best_score = score
                    best_bg = bg
        if best_bg:
            assignments[slug] = best_bg
        else:
            assignments[slug] = "_unclustered"

    # Group by assigned bigram
    clusters = defaultdict(list)
    for slug, bg in assignments.items():
        clusters[bg].append(slug)

    # Merge small clusters into nearest viable neighbor
    final_clusters = {}
    overflow = []
    for bg, slugs in clusters.items():
        if bg == "_unclustered" or len(slugs) < MIN_CLUSTER_SIZE:
            overflow.extend(slugs)
        else:
            final_clusters[bg] = slugs

    # Assign overflow articles to nearest cluster by token overlap
    if final_clusters and overflow:
        for slug in overflow:
            art_tokens = set(cat_articles[slug]["tokens"])
            best_cluster = None
            best_overlap = -1
            for bg, members in final_clusters.items():
                cluster_tokens = set()
                for m_slug in members[:5]:  # sample for speed
                    cluster_tokens.update(cat_articles[m_slug]["tokens"])
                overlap = len(art_tokens & cluster_tokens)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_cluster = bg
            if best_cluster:
                final_clusters[best_cluster].append(slug)
            else:
                # Last resort: put in largest cluster
                biggest = max(final_clusters.keys(), key=lambda k: len(final_clusters[k]))
                final_clusters[biggest].append(slug)
    elif overflow and not final_clusters:
        # No viable clusters found — create one big "general" cluster
        final_clusters["general"] = overflow

    # Cap clusters — merge smallest into nearest if too many
    while len(final_clusters) > MAX_CLUSTERS_PER_CAT:
        smallest_key = min(final_clusters.keys(), key=lambda k: len(final_clusters[k]))
        smallest_slugs = final_clusters.pop(smallest_key)
        # Merge into most similar remaining cluster
        s_tokens = set()
        for slug in smallest_slugs[:5]:
            s_tokens.update(cat_articles[slug]["tokens"])
        best_target = max(final_clusters.keys(),
                          key=lambda k: len(s_tokens & set(sum([cat_articles[s]["tokens"] for s in final_clusters[k][:5]], []))))
        final_clusters[best_target].extend(smallest_slugs)

    # Convert bigram names to clean cluster slugs
    named_clusters = {}
    for bg, slugs in final_clusters.items():
        cluster_slug = bg.replace(" ", "-") if bg != "general" else "general"
        # Ensure uniqueness
        if cluster_slug in named_clusters:
            cluster_slug += "-2"
        named_clusters[cluster_slug] = slugs

    return named_clusters


# ═══════════════════════════════════════════════════════════════
# Tier Assignment & Priority Scoring (site-agnostic)
# ═══════════════════════════════════════════════════════════════

def assign_tiers(articles, clusters_by_cat):
    """
    Assign siloTier and siloPriority to every article.
    Returns dict: {slug: {siloTier, siloCluster, siloParent, siloPriority}}

    Tier logic (site-agnostic):
      - pillar: longest article in cluster AND word_count >= PILLAR_THRESHOLD_WC
      - cluster: articles in clusters with 5+ members (mid-range word count)
      - support: everything else
      Hub pages are pre-existing and not part of this mapping.
    """
    silo_map = {}

    for cat, clusters in clusters_by_cat.items():
        hub_url = HUB_URLS.get(cat, f"/research/{cat}")

        for cluster_name, slugs in clusters.items():
            # Sort by word count descending — longest is candidate for pillar
            ranked = sorted(slugs, key=lambda s: articles[s]["word_count"], reverse=True)

            # Assign pillar (1 per cluster, must meet word count threshold)
            pillar_count = 0
            for i, slug in enumerate(ranked):
                art = articles[slug]
                wc = art["word_count"]

                if pillar_count < PILLAR_MAX_PER_CLUSTER and wc >= PILLAR_THRESHOLD_WC:
                    tier = "pillar"
                    pillar_count += 1
                    # Pillar's parent is the hub
                    parent = hub_url
                    # Priority: 90-100 for pillars
                    priority = min(100, 90 + int(wc / 500))
                else:
                    tier = "support"
                    # Support's parent is the pillar (if one exists) or the hub
                    pillar_slug = ranked[0] if articles[ranked[0]]["word_count"] >= PILLAR_THRESHOLD_WC else None
                    if pillar_slug and slug != pillar_slug:
                        parent = articles[pillar_slug]["url"]
                    else:
                        parent = hub_url
                    # Priority: based on position within cluster (higher wc = higher priority)
                    priority = max(10, 80 - i * 3)

                silo_map[slug] = {
                    "siloTier": tier,
                    "siloCluster": cluster_name,
                    "siloParent": parent,
                    "siloPriority": priority,
                    "category": cat,
                }

    return silo_map


def build_full_silo_map(category_filter=None):
    """Master function: load articles, cluster, assign tiers. Returns silo_map."""
    articles = load_articles(category_filter)
    cats = [category_filter] if category_filter else CATEGORIES

    clusters_by_cat = {}
    for cat in cats:
        clusters_by_cat[cat] = cluster_category(articles, cat)

    silo_map = assign_tiers(articles, clusters_by_cat)
    return articles, clusters_by_cat, silo_map


# ═══════════════════════════════════════════════════════════════
# Public API (for SemanticPipe / internal_linker integration)
# ═══════════════════════════════════════════════════════════════

_cached_silo_map = None

def get_silo_map(force_rebuild=False):
    """Lazy-load cached silo map."""
    global _cached_silo_map
    if _cached_silo_map is None or force_rebuild:
        _, _, _cached_silo_map = build_full_silo_map()
    return _cached_silo_map

def classify_article(slug):
    """Get silo classification for a single article."""
    smap = get_silo_map()
    return smap.get(slug, None)


# ═══════════════════════════════════════════════════════════════
# Analysis Report
# ═══════════════════════════════════════════════════════════════

def print_analysis(articles, clusters_by_cat, silo_map):
    """Print a detailed cluster analysis without writing anything."""
    total = len(silo_map)
    pillars = sum(1 for s in silo_map.values() if s["siloTier"] == "pillar")
    supports = sum(1 for s in silo_map.values() if s["siloTier"] == "support")

    print(f"\n{'='*70}")
    print(f"  SILO MAPPER ANALYSIS")
    print(f"{'='*70}")
    print(f"  Total articles:   {total}")
    print(f"  Pillars:          {pillars}")
    print(f"  Support:          {supports}")
    print(f"  Total clusters:   {sum(len(c) for c in clusters_by_cat.values())}")
    print()

    for cat in CATEGORIES:
        clusters = clusters_by_cat.get(cat, {})
        if not clusters:
            continue
        cat_articles = {s: a for s, a in articles.items() if a["category"] == cat}
        print(f"\n  --- {cat} ({len(cat_articles)} articles, {len(clusters)} clusters) ---")

        for cname, slugs in sorted(clusters.items(), key=lambda x: -len(x[1])):
            pillar_slugs = [s for s in slugs if silo_map.get(s, {}).get("siloTier") == "pillar"]
            avg_wc = sum(articles[s]["word_count"] for s in slugs) / len(slugs)
            print(f"\n    [{cname}] ({len(slugs)} articles, avg {avg_wc:.0f}w)")
            if pillar_slugs:
                for ps in pillar_slugs:
                    print(f"      * PILLAR: {articles[ps]['title'][:65]} ({articles[ps]['word_count']}w)")
            # Show a few support titles
            support_slugs = [s for s in slugs if s not in pillar_slugs][:3]
            for ss in support_slugs:
                print(f"        - {articles[ss]['title'][:65]} ({articles[ss]['word_count']}w)")
            if len(slugs) - len(pillar_slugs) > 3:
                print(f"        ... +{len(slugs) - len(pillar_slugs) - 3} more")

    print(f"\n{'='*70}")


# ═══════════════════════════════════════════════════════════════
# Apply Mode — Write frontmatter fields
# ═══════════════════════════════════════════════════════════════

def apply_silo_map(articles, silo_map, dry_run=False):
    """Write siloTier/siloCluster/siloParent/siloPriority into every article."""
    written = 0
    errors = 0
    for slug, silo in sorted(silo_map.items()):
        art = articles.get(slug)
        if not art:
            continue
        filepath = art["filepath"]
        try:
            if not dry_run:
                ok = write_silo_fields(
                    filepath,
                    silo["siloTier"],
                    silo["siloCluster"],
                    silo["siloParent"],
                    silo["siloPriority"],
                )
                if ok:
                    written += 1
                else:
                    errors += 1
            else:
                written += 1
        except Exception as e:
            print(f"  ERROR {slug}: {e}")
            errors += 1

    print(f"\n  Silo fields {'would be ' if dry_run else ''}written to {written} articles")
    if errors:
        print(f"  Errors: {errors}")
    return written


# ═══════════════════════════════════════════════════════════════
# Export Mode — JSON for tooling
# ═══════════════════════════════════════════════════════════════

def export_json(silo_map, output_path):
    """Export silo map as JSON for other tools to consume."""
    export = {}
    for slug, silo in silo_map.items():
        export[slug] = {
            "tier": silo["siloTier"],
            "cluster": silo["siloCluster"],
            "parent": silo["siloParent"],
            "priority": silo["siloPriority"],
            "category": silo["category"],
        }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export, f, indent=2, ensure_ascii=False)
    print(f"  Exported silo map to {output_path}")


# ═══════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Silo Mapper - SEO Pyramid Schema Generator")
    parser.add_argument("--analyze", action="store_true", help="Show cluster analysis (no writes)")
    parser.add_argument("--apply", action="store_true", help="Write silo fields to frontmatter")
    parser.add_argument("--dry-run", action="store_true", help="Preview apply without writing")
    parser.add_argument("--export", type=str, default=None, help="Export silo map to JSON file")
    parser.add_argument("--category", type=str, default=None, help="Filter to single category")
    args = parser.parse_args()

    if not args.analyze and not args.apply and not args.export:
        print("Use --analyze, --apply, or --export <path.json>")
        sys.exit(0)

    print("Loading articles and building clusters...")
    articles, clusters_by_cat, silo_map = build_full_silo_map(args.category)
    print(f"  {len(articles)} articles, {sum(len(c) for c in clusters_by_cat.values())} clusters")

    if args.analyze:
        print_analysis(articles, clusters_by_cat, silo_map)

    if args.apply:
        apply_silo_map(articles, silo_map, dry_run=args.dry_run)

    if args.export:
        export_json(silo_map, args.export)


if __name__ == "__main__":
    main()
