import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import internal_linker
print("Building inventory...")
inv = internal_linker.build_inventory()
print(f"  {len(inv)} articles indexed")
internal_linker.run_audit(inv)
