import os

root = r"e:\Mult_agent"
output_file = os.path.join(root, "codebase_dump.md")

skip_dirs = {".git", "__pycache__", "venv", "env", "node_modules", ".vscode", ".idea"}
skip_exts = {".pyc", ".pdf", ".exe", ".png", ".jpg", ".jpeg", ".zip", ".tar", ".gz", ".mp4", ".mp3", ".log", ".tmp", ".sqlite3"}
skip_files = {"codebase_dump.md", "update_dump.py", "update_dump_all.py", ".env"}

files_to_dump = []

for dirpath, dirnames, filenames in os.walk(root):
    # Filter directories in-place
    dirnames[:] = [d for d in dirnames if d not in skip_dirs]
    
    for f in filenames:
        if f in skip_files:
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext in skip_exts:
            continue
            
        full_path = os.path.join(dirpath, f)
        rel_path = os.path.relpath(full_path, root)
        
        files_to_dump.append(rel_path)

# Sort for consistent output
files_to_dump.sort()

with open(output_file, "w", encoding="utf-8") as out:
    out.write("# AI Agency Codebase Dump\n\nThis document contains the complete and current active codebase files.\n\n")
    for i, file in enumerate(files_to_dump, 1):
        out.write(f"---\n\n## {i}. {file.replace(os.sep, '/')}\n")
        path = os.path.join(root, file)
        ext = ""
        if file.endswith(".py"): ext = "python"
        elif file.endswith(".md"): ext = "markdown"
        elif file.endswith(".json"): ext = "json"
        elif file.endswith(".js"): ext = "javascript"
        elif file.endswith(".html"): ext = "html"
        elif file.endswith(".css"): ext = "css"
        
        out.write(f"```{ext}\n")
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                # To avoid breaking the markdown formatting with nested markdown code blocks,
                # we don't want triple backticks in the content to close the dump's code block early,
                # but standard markdown dumping usually ignores this unless properly escaped.
                # Just dumping raw for now.
                out.write(content)
        except UnicodeDecodeError:
            out.write(f"# Error: Could not decode file as UTF-8. It may be a binary file.")
        except Exception as e:
            out.write(f"# Error reading file: {e}")
        out.write("\n```\n\n")

print(f"codebase_dump.md updated successfully with {len(files_to_dump)} files.")
