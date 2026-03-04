import os
c = sum(1 for r, d, f in os.walk('dist/research') for fi in f if fi.endswith('.html'))
print('Total research pages:', c)
