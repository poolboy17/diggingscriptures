import os
base = "src/content"
types = ["hubs","places","routes","stories","context"]
for t in types:
    d = os.path.join(base, t)
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"): continue
        path = os.path.join(d, f)
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        for i, line in enumerate(lines[:20]):
            if line.startswith("description:"):
                # Check for nested unescaped quotes
                val = line[len("description:"):].strip()
                if val.startswith('"') and val.count('"') > 2:
                    print(f"BROKEN: {t}/{f} line {i+1}: {val[:100]}")
                break
print("Done.")
