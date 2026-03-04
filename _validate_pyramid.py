"""
Silo Pyramid Validator
======================
Validates internal linking flows through the full SEO pyramid:
  TOP-DOWN:  Hub -> Pillar -> Support (every level links down)
  BOTTOM-UP: Support -> Pillar -> Hub (every level links up)

Tests EVERY silo (category) and EVERY cluster within each silo.
Reports broken chains and missing links.
"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import internal_linker

print("Building inventory for pyramid validation...")
inv = internal_linker.build_inventory()
print(f"  {len(inv)} articles indexed\n")

# Group articles by category and cluster
CATEGORIES = internal_linker.CATEGORIES
HUB_URLS = internal_linker.HUB_URLS

clusters = {}  # {cat: {cluster_name: [slugs]}}
for slug, info in inv.items():
    cat = info["category"]
    cluster = info.get("silo_cluster", "")
    if not cluster:
        continue
    clusters.setdefault(cat, {}).setdefault(cluster, []).append(slug)

total_pass = 0
total_fail = 0
total_warn = 0
results = []

SEP = "=" * 70
SUBSEP = "-" * 50

print(f"{SEP}")
print(f"  SILO PYRAMID VALIDATION")
print(f"  Testing: Hub <-> Pillar <-> Support linking in every silo")
print(f"{SEP}\n")

for cat in CATEGORIES:
    hub_url = HUB_URLS.get(cat, "")
    cat_clusters = clusters.get(cat, {})
    cat_articles = {s: i for s, i in inv.items() if i["category"] == cat}
    pillars = [s for s, i in cat_articles.items() if i.get("silo_tier") == "pillar"]
    supports = [s for s, i in cat_articles.items() if i.get("silo_tier") == "support"]

    print(f"\n  SILO: {cat}")
    print(f"  Hub: {hub_url}")
    print(f"  {len(cat_clusters)} clusters | {len(pillars)} pillars | {len(supports)} support")
    print(f"  {SUBSEP}")

    # ── TEST 1: BOTTOM-UP — Support -> Pillar ──────────────────
    print(f"\n  [BOTTOM-UP] Support -> Pillar (via siloParent or outbound link)")
    support_to_pillar_ok = 0
    support_to_pillar_fail = 0
    support_fail_examples = []

    for slug in supports:
        info = inv[slug]
        parent_url = info.get("silo_parent", "")
        outbound = info["outbound_links"]

        # Check: does support link to its siloParent (pillar)?
        links_to_parent = parent_url in outbound
        # Also check if it links to ANY pillar in same cluster
        cluster_name = info.get("silo_cluster", "")
        cluster_pillars = [s for s in pillars if inv[s].get("silo_cluster") == cluster_name]
        links_to_any_pillar = any(inv[p]["url"] in outbound for p in cluster_pillars)

        if links_to_parent or links_to_any_pillar:
            support_to_pillar_ok += 1
        else:
            support_to_pillar_fail += 1
            if len(support_fail_examples) < 3:
                support_fail_examples.append(f"    FAIL: {slug[:55]} -> parent={parent_url[:40]}")

    status = "PASS" if support_to_pillar_fail == 0 else "PARTIAL"
    print(f"    {support_to_pillar_ok}/{len(supports)} support articles link to pillar  [{status}]")
    for ex in support_fail_examples:
        print(ex)
    total_pass += support_to_pillar_ok
    total_fail += support_to_pillar_fail

    # ── TEST 2: BOTTOM-UP — Support -> Hub ─────────────────────
    print(f"\n  [BOTTOM-UP] Support -> Hub (via hub link in body)")
    support_to_hub_ok = 0
    support_to_hub_fail = 0
    for slug in supports:
        outbound = inv[slug]["outbound_links"]
        if any(link.rstrip("/") == hub_url for link in outbound):
            support_to_hub_ok += 1
        else:
            support_to_hub_fail += 1
    status = "PASS" if support_to_hub_fail == 0 else "PARTIAL"
    print(f"    {support_to_hub_ok}/{len(supports)} support articles link to hub  [{status}]")
    total_pass += support_to_hub_ok
    total_fail += support_to_hub_fail

    # ── TEST 3: BOTTOM-UP — Pillar -> Hub ──────────────────────
    print(f"\n  [BOTTOM-UP] Pillar -> Hub")
    pillar_to_hub_ok = 0
    pillar_to_hub_fail = 0
    for slug in pillars:
        outbound = inv[slug]["outbound_links"]
        if any(link.rstrip("/") == hub_url for link in outbound):
            pillar_to_hub_ok += 1
        else:
            pillar_to_hub_fail += 1
    status = "PASS" if pillar_to_hub_fail == 0 else "PARTIAL"
    print(f"    {pillar_to_hub_ok}/{len(pillars)} pillar articles link to hub  [{status}]")
    total_pass += pillar_to_hub_ok
    total_fail += pillar_to_hub_fail

    # ── TEST 4: TOP-DOWN — Pillar -> Support (same cluster) ────
    print(f"\n  [TOP-DOWN] Pillar -> Support (links to cluster siblings)")
    pillar_to_support_ok = 0
    pillar_to_support_fail = 0
    pillar_down_examples = []
    for slug in pillars:
        info = inv[slug]
        outbound = info["outbound_links"]
        cluster_name = info.get("silo_cluster", "")
        cluster_supports = [s for s in supports if inv[s].get("silo_cluster") == cluster_name]
        # Does the pillar link to at least one support in same cluster?
        links_to_cluster = sum(1 for s in cluster_supports if inv[s]["url"] in outbound)
        if links_to_cluster > 0:
            pillar_to_support_ok += 1
        else:
            pillar_to_support_fail += 1
            if len(pillar_down_examples) < 2:
                pillar_down_examples.append(f"    FAIL: {slug[:55]} (cluster={cluster_name})")
    status = "PASS" if pillar_to_support_fail == 0 else "PARTIAL"
    print(f"    {pillar_to_support_ok}/{len(pillars)} pillars link to cluster support articles  [{status}]")
    for ex in pillar_down_examples:
        print(ex)
    total_pass += pillar_to_support_ok
    total_fail += pillar_to_support_fail

    # ── TEST 5: Cluster cohesion — siblings link to each other ─
    print(f"\n  [COHESION] Intra-cluster linking (siblings link to siblings)")
    cohesive_clusters = 0
    weak_clusters = 0
    for cname, c_slugs in cat_clusters.items():
        if len(c_slugs) < 2:
            continue
        c_urls = {inv[s]["url"] for s in c_slugs}
        cross_links = 0
        for s in c_slugs:
            for link in inv[s]["outbound_links"]:
                if link in c_urls and link != inv[s]["url"]:
                    cross_links += 1
        avg_cross = cross_links / len(c_slugs)
        if avg_cross >= 1.0:
            cohesive_clusters += 1
        else:
            weak_clusters += 1
    total_c = cohesive_clusters + weak_clusters
    status = "PASS" if weak_clusters == 0 else "PARTIAL"
    print(f"    {cohesive_clusters}/{total_c} clusters have avg >= 1 cross-link  [{status}]")
    total_pass += cohesive_clusters
    total_warn += weak_clusters

# ── SUMMARY ────────────────────────────────────────────────────
print(f"\n\n{SEP}")
print(f"  PYRAMID VALIDATION SUMMARY")
print(f"{SEP}")
print(f"  Total checks passed:   {total_pass}")
print(f"  Total checks failed:   {total_fail}")
print(f"  Total warnings:        {total_warn}")
print(f"  Overall:               {'ALL PASS' if total_fail == 0 else 'ISSUES FOUND'}")
print(f"{SEP}")

# Per-silo one-line summary
print(f"\n  PER-SILO BREAKDOWN:")
for cat in CATEGORIES:
    cat_articles = {s: i for s, i in inv.items() if i["category"] == cat}
    hub_url = HUB_URLS.get(cat, "")
    pillars_cat = [s for s, i in cat_articles.items() if i.get("silo_tier") == "pillar"]
    supports_cat = [s for s, i in cat_articles.items() if i.get("silo_tier") == "support"]

    # Count support->hub
    s2h = sum(1 for s in supports_cat if any(l.rstrip("/") == hub_url for l in inv[s]["outbound_links"]))
    # Count support->pillar
    s2p = 0
    for s in supports_cat:
        parent = inv[s].get("silo_parent", "")
        if parent in inv[s]["outbound_links"]:
            s2p += 1
        else:
            cluster = inv[s].get("silo_cluster", "")
            cp = [p for p in pillars_cat if inv[p].get("silo_cluster") == cluster]
            if any(inv[p]["url"] in inv[s]["outbound_links"] for p in cp):
                s2p += 1
    # Count pillar->hub
    p2h = sum(1 for p in pillars_cat if any(l.rstrip("/") == hub_url for l in inv[p]["outbound_links"]))

    print(f"    {cat:25s}  support->hub={s2h}/{len(supports_cat)}  support->pillar={s2p}/{len(supports_cat)}  pillar->hub={p2h}/{len(pillars_cat)}")

print(f"\n{SEP}")
