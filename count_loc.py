import os

# Directories to exclude
EXCLUDE_DIRS = {
    '.venv', 'venv', 'env', '.git', 'node_modules', 'staticfiles', 
    'media', '.vscode', 'dist', 'build', '.expo', '__pycache__', '.pytest_cache'
}

# File extensions grouped by language/type
CODE_EXTENSIONS = {
    'Python (.py)': ['.py'],
    'HTML Templates (.html)': ['.html', '.htm'],
    'CSS / SCSS (.css, .scss)': ['.css', '.scss'],
    'JavaScript (.js, .jsx)': ['.js', '.jsx'],
    'TypeScript / React (.ts, .tsx)': ['.ts', '.tsx'],
    'JSON / YAML (.json, .yaml, .yml)': ['.json', '.yml', '.yaml'],
    'Markdown (.md)': ['.md'],
    'Batch / Shell (.bat, .sh)': ['.bat', '.sh'],
    'SQL (.sql)': ['.sql']
}

ext_map = {ext: lang for lang, exts in CODE_EXTENSIONS.items() for ext in exts}
stats = {}

workspace_dir = "."

for root, dirs, files in os.walk(workspace_dir):
    # Skip excluded directories
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
    
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext in ext_map:
            lang = ext_map[ext]
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    total = len(lines)
                    non_blank = sum(1 for l in lines if l.strip())
                    if lang not in stats:
                        stats[lang] = {'files': 0, 'lines': 0, 'code': 0}
                    stats[lang]['files'] += 1
                    stats[lang]['lines'] += total
                    stats[lang]['code'] += non_blank
            except Exception:
                pass

print("-" * 75)
print(f"{'Language / File Type':<35} | {'Files':<7} | {'Total Lines':<12} | {'Code Lines':<12}")
print("-" * 75)
total_files = total_lines = total_code = 0
for lang, s in sorted(stats.items(), key=lambda x: x[1]['lines'], reverse=True):
    print(f"{lang:<35} | {s['files']:<7} | {s['lines']:<12} | {s['code']:<12}")
    total_files += s['files']
    total_lines += s['lines']
    total_code += s['code']
print("-" * 75)
print(f"{'TOTAL':<35} | {total_files:<7} | {total_lines:<12} | {total_code:<12}")
print("-" * 75)
