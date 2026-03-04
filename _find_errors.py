import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('_deploy_log7.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'error' in line.lower():
        # Print surrounding context
        start = max(0, i - 3)
        for j in range(start, min(len(lines), i + 3)):
            print(f'{j}: {lines[j].rstrip()}')
        print('---')
