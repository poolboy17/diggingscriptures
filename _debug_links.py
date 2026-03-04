import sys
sys.path.insert(0, '.')
from internal_linker import build_inventory

inv = build_inventory()
all_links = set()
for s, i in inv.items():
    for l in i['outbound_links']:
        all_links.add(l)

print(f"Total unique outbound URLs: {len(all_links)}")
print("Sample links:")
for l in sorted(all_links)[:30]:
    print(f"  {l}")

# Check URL format of inventory
print("\nSample article URLs (from inventory):")
for s in sorted(inv.keys())[:10]:
    print(f"  {inv[s]['url']}")
