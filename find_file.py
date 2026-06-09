import os

target = "make_real_time.py"
print(f"Searching for '{target}'...")

found = False
for root, dirs, files in os.walk('.'):
    if target in files:
        print("Found at:", os.path.join(root, target))
        found = True

if not found:
    print("Not found in current directory and subdirectories.")
