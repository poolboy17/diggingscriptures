import os, re
base = "src/content"
types = ["hubs","places","routes","stories","context"]
fixed = 0
for t in types:
    d = os.path.join(base, t)
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"): continue
        path = os.path.join(d, f)
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
        # Fix quoted dates: lastUpdated: "2026-01-25" -> lastUpdated: 2026-01-25
        new_content = re.sub(
            r'(lastUpdated:\s*)"(\d{4}-\d{2}-\d{2})"',
            r'\g<1>\2',
            content
        )
        if new_content != content:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new_content)
            fixed += 1
            print(f"  Fixed: {t}/{f}")
print(f"\nFixed {fixed} files.")
