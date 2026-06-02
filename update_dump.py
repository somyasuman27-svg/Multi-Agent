import os

root = r"e:\Mult_agent"
files_to_dump = [
    ".geminiignore",
    "config.py",
    "api_bridge.py",
    "manager.py",
    "auto_run.py",
    "sanity_check_v2.py",
    "test_draft_coder.py",
    "test_gem.py"
]

# Add files in agency
for f in os.listdir(os.path.join(root, "agency")):
    if f.endswith(".py") and not f.startswith("__"):
        files_to_dump.append(f"agency/{f}")

with open(os.path.join(root, "codebase_dump.md"), "w", encoding="utf-8") as out:
    out.write("# AI Agency Codebase Dump\n\nThis document contains the complete and current active core codebase files for the multi-agent development architecture. It excludes any temporary agent-generated outputs or project codebases to maintain token efficiency and clean project state.\n\n")
    for i, file in enumerate(files_to_dump, 1):
        out.write(f"---\n\n## {i}. {os.path.basename(file)}\n")
        path = os.path.join(root, file)
        ext = "python" if file.endswith(".py") else ""
        out.write(f"```{ext}\n")
        try:
            with open(path, "r", encoding="utf-8") as f:
                out.write(f.read().strip())
        except Exception as e:
            out.write(f"# Error reading file: {e}")
        out.write("\n```\n\n")

print("codebase_dump.md updated successfully.")
