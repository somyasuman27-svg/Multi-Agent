"""
agency/triage.py — Antigravity CLI Team Triage System
=====================================================
Ollama-powered issue classification + team-specific logging + department pipelines.

Departments:
  🔧 RnD (Code Team)   — code logic, bugs, architecture, backend
  🎨 UI/UX (Design Team) — CSS, layout, colors, fonts, animations, responsiveness
"""
import os
import re
import glob
import requests
from datetime import datetime
from config import PATHS, ROOT_DIR
from agency.execution import read_file, write_file, append_file


# =====================================================================
# 🧠 OLLAMA ISSUE CLASSIFIER
# =====================================================================

def ollama_triage_issue(user_comment: str, project_context: str = "") -> str:
    """
    Asks Ollama to classify a user's issue/comment into a department.
    Returns: 'code_issue' | 'design_issue' | 'both' | 'unsure'
    """
    prompt = f"""You are an expert issue triage classifier for a software development agency.
A user has reported an issue or requested a change on an existing project.

PROJECT CONTEXT (files, recent logs):
{project_context[:3000]}

USER'S COMMENT/ISSUE:
"{user_comment}"

Classify this issue into EXACTLY ONE of these categories:
- code_issue: Bug in Python/backend logic, API errors, server crashes, import failures,
  database issues, broken routes, missing functions, wrong calculations, test failures
  caused by logic errors.
- design_issue: Visual problems — wrong colors, bad fonts, layout broken, CSS issues,
  spacing problems, responsiveness broken, animations not working, hover effects missing,
  ugly appearance, UI polish needed, HTML structure/template issues.
- both: Issue clearly spans BOTH code logic AND visual design.
- unsure: You cannot confidently classify — need human clarification.

IMPORTANT: Think carefully. "Button doesn't work" = code_issue (event handler broken).
"Button looks ugly" = design_issue (styling). "Button doesn't work and looks ugly" = both.

Respond with ONLY one word: code_issue, design_issue, both, or unsure
Do NOT include any other text, reasoning, or formatting."""

    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3:latest",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=120
        )
        if res.status_code == 200:
            raw = res.json().get("response", "unsure").strip().lower()
            # Clean thinking tags if model outputs them
            raw = re.sub(r'<think>.*?(?:</think>|$)', '', raw, flags=re.DOTALL).strip()
            # Extract the classification keyword
            for keyword in ["code_issue", "design_issue", "both"]:
                if keyword in raw:
                    return keyword
            return "unsure"
        return "unsure"
    except Exception as e:
        print(f"⚠️ Ollama triage error: {e}")
        return "unsure"


def ask_user_triage() -> str:
    """Fallback: ask the user to manually classify the issue."""
    mapping = {"1": "code_issue", "2": "design_issue", "3": "both"}
    while True:
        print("\n🤔 Ollama couldn't confidently classify this issue.")
        print("Please select the department:")
        print("═" * 50)
        print("1. 🔧 RnD (Code Team)      — Backend / logic / bugs")
        print("2. 🎨 UI/UX (Design Team)  — CSS / layout / visuals")
        print("3. 🔧🎨 Both               — Code + Design")
        print("═" * 50)
        choice = input("Select (1/2/3): ").strip()
        if choice in mapping:
            return mapping[choice]
        print("❌ Invalid selection. Please choose 1, 2, or 3.")


# =====================================================================
# 📋 TEAM-SPECIFIC LOGGING
# =====================================================================

def _get_log_path(department: str, project_paths: dict) -> str:
    """Returns the log file path for a specific department."""
    mgmt_dir = os.path.join(project_paths["root"], "0_Management")
    os.makedirs(mgmt_dir, exist_ok=True)
    if department == "rnd":
        return os.path.join(mgmt_dir, "rnd_issues.log")
    elif department == "uiux":
        return os.path.join(mgmt_dir, "uiux_issues.log")
    return os.path.join(mgmt_dir, "general_issues.log")


def log_issue(department: str, project_paths: dict,
              issue_description: str, classification: str,
              result: str = "pending", agents_used: str = ""):
    """Writes a timestamped entry to the team-specific log file."""
    log_path = _get_log_path(department, project_paths)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"""════════════════════════════════════════════════════
[{timestamp}] DEPARTMENT: {department.upper()}
Classification: {classification}
Issue: {issue_description[:300]}
Agents: {agents_used}
Result: {result}
════════════════════════════════════════════════════
"""
    append_file(log_path, entry)
    print(f"📝 Logged to {os.path.basename(log_path)}")


def read_team_log(department: str, project_paths: dict) -> str:
    """Reads the log for a specific team. Returns content or 'empty' message."""
    log_path = _get_log_path(department, project_paths)
    content = read_file(log_path)
    if not content:
        return f"📭 No {department.upper()} issues logged yet."
    return content


# =====================================================================
# 🔧 RND TEAM PIPELINE (Code Issues)
# =====================================================================

def run_rnd_pipeline(briefing: dict, project_paths: dict) -> str:
    """
    Runs the RnD code-fix pipeline:
    DRAFT_CODER → LOGIC_EXPANDER → DEEP_TESTER
    Wraps existing agency functions.
    """
    from agency.patching import phase_patch_draft_coder, prune_error
    from agency.orchestration import (
        phase_2b_logic_expander, phase_3_a_test_lead,
        phase_3_b_deep_tester
    )

    print("\n🔧 ════════════════════════════════════════")
    print("   RnD TEAM PIPELINE — CODE FIX")
    print("   ════════════════════════════════════════")

    user_input = briefing.get("task", "Fix code issues")
    project_name = briefing.get("project_name", "unknown")

    # Load existing test logs for context
    testing_dir = project_paths.get("testing", "")
    error_report = ""
    if testing_dir and os.path.exists(testing_dir):
        log_files = glob.glob(os.path.join(testing_dir, "test_execution_v*.log"))
        if log_files:
            def get_log_version(fp):
                match = re.search(r'test_execution_v(\d+)\.log$', os.path.basename(fp))
                return int(match.group(1)) if match else 0
            latest_log = max(log_files, key=get_log_version)
            print(f"📋 Found existing test log: {os.path.basename(latest_log)}")
            error_report = prune_error(read_file(latest_log))

    fix_attempt = 0
    max_fix_attempts = 3
    success = False
    result_status = "failed"

    while fix_attempt < max_fix_attempts:
        fix_attempt += 1
        print(f"\n🔄 RnD FIX CYCLE {fix_attempt}/{max_fix_attempts}")

        patched = phase_patch_draft_coder(
            briefing, project_paths,
            error_report=error_report,
            max_attempts=1
        )
        if not patched:
            print("❌ RnD patch failed — stopping fix cycle")
            break

        phase_2b_logic_expander(briefing, project_paths)

        compiled_res = phase_3_a_test_lead(briefing)
        if compiled_res:
            compiled, smoke_report = compiled_res
            exec_log, deep_verdict = phase_3_b_deep_tester(
                compiled, briefing, project_paths
            )

            passed = "fail" not in deep_verdict.lower() and "error" not in deep_verdict.lower()
            if passed:
                print(f"✅ RnD fix verified after {fix_attempt} attempt(s)")
                success = True
                result_status = f"SUCCESS on attempt {fix_attempt}"
                break
            else:
                error_report = prune_error(exec_log)
                print(f"⚠️ Tests failed. Preparing attempt {fix_attempt + 1}...")

    if not success:
        result_status = f"FAILED after {max_fix_attempts} attempts"
        print("❌ RnD pipeline exhausted. Manual review required.")

    # Log the result
    log_issue("rnd", project_paths, user_input, "code_issue",
              result_status, "DRAFT_CODER→LOGIC_EXPANDER→DEEP_TESTER")

    return result_status


# =====================================================================
# 🎨 UI/UX TEAM PIPELINE (Design Issues)
# =====================================================================

def run_uiux_pipeline(briefing: dict, project_paths: dict) -> str:
    """
    Runs the UI/UX design-fix pipeline:
    Targets ONLY CSS/HTML/template files — never touches Python backend.
    Uses DRAFT_CODER with design-specific instructions.
    """
    from agency.patching import extract_code_block
    from agency.memory import inject_memory_into_prompt
    from api_bridge import call_agent

    print("\n🎨 ════════════════════════════════════════")
    print("   UI/UX TEAM PIPELINE — DESIGN FIX")
    print("   ════════════════════════════════════════")

    user_input = briefing.get("task", "Fix design issues")
    project_name = briefing.get("project_name", "unknown")
    project_root = project_paths["root"]

    # Collect all design-relevant files
    design_files = {}
    design_search_patterns = [
        ("templates", "*.html"),
        ("static/css", "*.css"),
        ("static/js", "*.js"),
    ]

    for subdir, pattern in design_search_patterns:
        search_dir = os.path.join(project_root, subdir)
        if os.path.exists(search_dir):
            found = glob.glob(os.path.join(search_dir, "**", pattern), recursive=True)
            for f in found:
                rel_path = os.path.relpath(f, project_root)
                content = read_file(f)
                if content:
                    design_files[rel_path] = content

    if not design_files:
        print("⚠️ No design files (HTML/CSS/JS) found in project.")
        log_issue("uiux", project_paths, user_input, "design_issue",
                  "SKIPPED — no design files found", "ANTIGRAVITY_DESIGNER")
        return "skipped"

    # Build context of current design files
    design_context = ""
    for rel_path, content in design_files.items():
        design_context += f"\n==== FILE: {rel_path} ====\n{content}\n==== END FILE ====\n"

    instruction = """You are the UI/UX DESIGN LEAD performing a targeted design fix.
You will receive the current HTML, CSS, and JS files for a web project.
Apply ONLY the visual/design changes requested by the user.

STRICT RULES:
1. NEVER modify Python backend code (final_code.py).
2. ONLY change CSS properties, HTML structure, fonts, colors, spacing, animations.
3. Output ALL modified files using this EXACT format for each file:
   ==== FILE: path/to/filename.ext ====
   ... complete corrected file content ...
   ==== END FILE ====
4. Only output files you actually changed. Do NOT output unchanged files.
5. Do NOT add any conversational text or explanations."""

    prompt = f"""PROJECT: {project_name}
DESIGN CHANGE REQUESTED: {user_input}

CURRENT DESIGN FILES:
{design_context}

Apply the requested design changes. Output only the modified files."""

    print("⏳ Antigravity UI/UX Designer is analyzing and fixing the design...")
    prompt_with_mem = inject_memory_into_prompt("ANTIGRAVITY_DESIGNER", project_paths, prompt)
    raw_response = call_agent("ANTIGRAVITY_DESIGNER", instruction, prompt_with_mem,
                              project_dir=project_root)

    # Extract and apply patched files
    from agency.patching import extract_all_files
    patched_files = extract_all_files(raw_response)

    if not patched_files:
        # Fallback: try to extract a single code block
        code = extract_code_block(raw_response, lang="html")
        if not code:
            code = extract_code_block(raw_response, lang="css")
        if code:
            # Try to guess which file it belongs to
            if "<html" in code.lower() or "<body" in code.lower():
                patched_files = {"templates/index.html": code}
            else:
                patched_files = {"static/css/style.css": code}

    if not patched_files:
        print("❌ Antigravity UI/UX Designer returned no usable patches.")
        log_issue("uiux", project_paths, user_input, "design_issue",
                  "FAILED — no patches returned", "ANTIGRAVITY_DESIGNER")
        return "failed"

    files_changed = 0
    for rel_path, content in patched_files.items():
        full_path = os.path.join(project_root, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        write_file(full_path, content)
        print(f"🎨 Design patch applied: {rel_path}")
        files_changed += 1

    result_status = f"SUCCESS — {files_changed} design file(s) updated"
    print(f"\n✅ UI/UX pipeline complete. {files_changed} file(s) patched.")

    log_issue("uiux", project_paths, user_input, "design_issue",
              result_status, "ANTIGRAVITY_DESIGNER")

    return result_status


# =====================================================================
# 📊 TEAM LOG VIEWER
# =====================================================================

def display_team_logs(project_paths: dict):
    """Interactive viewer for team-specific issue logs."""
    print("\n📊 ════════════════════════════════════════")
    print("   TEAM ISSUE LOGS")
    print("   ════════════════════════════════════════")
    print("1. 🔧 RnD (Code Team) Logs")
    print("2. 🎨 UI/UX (Design Team) Logs")
    print("3. 📋 Both Logs")
    print("═" * 50)
    choice = input("Select (1/2/3): ").strip()

    if choice in ("1", "3"):
        print("\n🔧 ── RnD ISSUE LOG ──────────────────────")
        rnd_log = read_team_log("rnd", project_paths)
        print(rnd_log[-3000:] if len(rnd_log) > 3000 else rnd_log)

    if choice in ("2", "3"):
        print("\n🎨 ── UI/UX ISSUE LOG ────────────────────")
        uiux_log = read_team_log("uiux", project_paths)
        print(uiux_log[-3000:] if len(uiux_log) > 3000 else uiux_log)

    if choice not in ("1", "2", "3"):
        print("❌ Invalid selection.")
