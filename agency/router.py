import os
import re
import sys
import time
import requests
from config import PATHS, ROOT_DIR
from agency.execution import read_file, write_file, append_file
from agency.testing import check_playwright_available

def call_ollama_direct(prompt: str) -> str:
    """Direct Ollama API call for routing decisions."""
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
            return res.json().get("response", "UNSURE").strip()
        return "UNSURE"
    except Exception as e:
        print(f"Ollama error: {e}")
        return "UNSURE"

def ollama_classify_action(user_input: str, project_name: str) -> str:
    """
    Ollama classifies what action to take on existing project.
    Returns: patch / fix / rebuild
    If unsure — asks user directly.
    """
    prompt = f"""You are a task classifier for a development agency.
A developer wants to update project '{project_name}'.
Their request: "{user_input}"

Classify this as ONE of these actions:
- patch: Simple change. Add comments, rename variables, 
         update text, minor styling. ONE agent needed.
- fix: Bug fix or logic update. Needs Draft + Logic + Test.
- rebuild: Major overhaul. Needs full pipeline.

If you are NOT confident (less than 80% sure) — respond with: UNSURE

Respond with ONLY one word: patch, fix, rebuild, or UNSURE"""

    response = call_ollama_direct(prompt).lower()
    
    action = "unsure"
    for keyword in ["patch", "fix", "rebuild"]:
        if keyword in response:
            # If multiple matches, we might just take the first. But typically it says one word.
            action = keyword
            break
    
    if action == "unsure" or action not in ["patch", "fix", "rebuild"]:
        # Ask user directly
        print("\n🤔 Ollama is unsure. Please clarify:")
        print("1. patch  — Simple change (comments, text, minor style)")
        print("2. fix    — Bug fix (needs testing)")  
        print("3. rebuild — Full rebuild from scratch")
        manual = input("Select (1/2/3): ").strip()
        mapping = {"1": "patch", "2": "fix", "3": "rebuild"}
        action = mapping.get(manual, "fix")
    
    print(f"🎯 Action classified: {action.upper()}")
    return action

def update_change_log(project_paths: dict, change: str, 
                      mode: str, agents: str, result: str, attempt: int = 1):
    """Appends entry to project change_log.md"""
    from datetime import datetime
    entry = f"""════════════════════════════════
[{datetime.now().strftime('%Y-%m-%d %H:%M')}] MODE: {mode} [Attempt: {attempt}]
Change: {change[:150]}
Agents: {agents}
Result: {result}
════════════════════════════════
"""
    change_log_path = os.path.join(
        project_paths["root"], "0_Management", "change_log.md"
    )
    append_file(change_log_path, entry)

def startup_menu(base_workspace: str) -> dict:
    """
    Ollama-powered interactive startup menu.
    Returns routing decision: new project, existing project action, or antigravity triage.
    """
    if os.getenv("AUTO_MODE") == "new":
        print("🤖 [AUTO MODE] Automatically selecting New Project Pipeline.")
        return {"mode": "new"}
        
    print("\n" + "═" * 50)
    print("🤖 AI AGENCY — AUTONOMOUS DEVELOPMENT SYSTEM")
    print("═" * 50)
    print("1. New Project")
    print("2. Existing Project (Classic Mode)")
    print("3. 🚀 Antigravity Mode (Team Triage)")
    print("═" * 50)
    
    choice = input("Select (1/2/3): ").strip()
    
    if choice == "1":
        return {"mode": "new"}
    
    elif choice in ("2", "3"):
        # List existing projects
        projects = []
        if os.path.exists(base_workspace):
            projects = [d for d in os.listdir(base_workspace) 
                       if os.path.isdir(os.path.join(base_workspace, d))]
        
        if not projects:
            print("❌ No existing projects found.")
            return {"mode": "new"}
        
        print("\n📁 YOUR PROJECTS:")
        print("═" * 50)
        for i, p in enumerate(projects, 1):
            print(f"{i}. {p}")
        print("═" * 50)
        
        proj_choice = input("Select project number: ").strip()
        try:
            selected = projects[int(proj_choice) - 1]
        except (ValueError, IndexError):
            print("❌ Invalid selection.")
            return {"mode": "new"}
        
        project_root = os.path.join(base_workspace, selected)
        
        if choice == "3":
            # Antigravity Mode — Team Triage
            return {
                "mode": "antigravity",
                "project": selected,
                "project_root": project_root
            }
        
        # Classic existing project mode (choice == "2")
        # Show project changelog
        change_log_path = os.path.join(project_root, "0_Management", "change_log.md")
        change_log = read_file(change_log_path)
        
        if change_log:
            print(f"\n📋 CHANGE LOG — {selected}:")
            print("═" * 50)
            print(change_log[-2000:])  # Show last 2000 chars only
            print("═" * 50)
        
        # Get user's change description
        print(f"\n💬 What do you want to do with {selected}?")
        user_input = input("> ").strip()
        
        # Ollama classifies the action
        action = ollama_classify_action(user_input, selected)
        
        return {
            "mode": "existing",
            "project": selected,
            "project_root": project_root,
            "user_input": user_input,
            "action": action
        }
    
    return {"mode": "new"}


def antigravity_triage_flow(routing: dict, base_workspace: str):
    """
    Antigravity Mode: Ollama-powered team triage for existing projects.
    Classifies issues as code/design/both and routes to the correct department.
    """
    from agency.triage import (
        ollama_triage_issue, ask_user_triage,
        run_rnd_pipeline, run_uiux_pipeline,
        display_team_logs, log_issue
    )
    
    project_name = routing["project"]
    project_root = routing["project_root"]
    
    project_paths = {
        "root": project_root,
        "management": os.path.join(project_root, "0_Management"),
        "research": os.path.join(project_root, "1_Research"),
        "drafts": os.path.join(project_root, "2_Source_Control", "Drafts"),
        "production": os.path.join(project_root, "2_Source_Control",
                                   "04_Production", "final_code.py"),
        "testing": os.path.join(project_root, "3_Testing")
    }
    
    # Update global PATHS
    PATHS["root"] = project_paths["root"]
    PATHS["testing"] = project_paths["testing"]
    PATHS["production"] = project_paths["production"]
    PATHS["draft_skeleton"] = os.path.join(project_paths["drafts"], "draft.py")
    PATHS["raw_research"] = os.path.join(project_paths["research"], "research_log.md")
    
    existing_code = read_file(project_paths["production"])
    
    print(f"\n🚀 ANTIGRAVITY MODE — {project_name}")
    print("═" * 50)
    print("1. 📝 Report an Issue / Request a Change")
    print("2. 📊 View Team Logs")
    print("═" * 50)
    
    sub_choice = input("Select (1/2): ").strip()
    
    if sub_choice == "2":
        display_team_logs(project_paths)
        return
    
    # Get user's issue description
    print(f"\n💬 Describe the issue or change you want for {project_name}:")
    user_input = input("> ").strip()
    
    if not user_input:
        print("❌ No input provided.")
        return
    
    # Build project context for Ollama
    project_context = f"Project: {project_name}\n"
    if existing_code:
        project_context += f"Backend code (first 1000 chars):\n{existing_code[:1000]}\n"
    
    # Check for design files
    html_path = os.path.join(project_root, "templates", "index.html")
    if os.path.exists(html_path):
        html_content = read_file(html_path)
        project_context += f"HTML template (first 500 chars):\n{html_content[:500]}\n"
    
    css_path = os.path.join(project_root, "static", "css", "style.css")
    if os.path.exists(css_path):
        css_content = read_file(css_path)
        project_context += f"CSS (first 500 chars):\n{css_content[:500]}\n"
    
    # Ollama triage classification
    print("\n🧠 Ollama is analyzing your issue...")
    classification = ollama_triage_issue(user_input, project_context)
    
    if classification == "unsure":
        classification = ask_user_triage()
    
    # Display classification result
    dept_labels = {
        "code_issue": "🔧 RnD (Code Team)",
        "design_issue": "🎨 UI/UX (Design Team)",
        "both": "🔧🎨 Both Teams"
    }
    print(f"\n🎯 Classification: {dept_labels.get(classification, classification)}")
    
    # Build briefing for pipelines
    briefing = {
        "project_name": project_name,
        "project": project_name,
        "task": user_input,
        "brief": user_input,
        "existing_code": existing_code,
        "mode": "fix",
        "complexity": "complex"
    }
    
    # Route to the correct department
    if classification == "code_issue":
        run_rnd_pipeline(briefing, project_paths)
        
    elif classification == "design_issue":
        run_uiux_pipeline(briefing, project_paths)
        
    elif classification == "both":
        print("\n📋 Running BOTH pipelines sequentially...")
        print("─" * 50)
        run_uiux_pipeline(briefing, project_paths)
        print("\n" + "─" * 50)
        run_rnd_pipeline(briefing, project_paths)
    
    from agency.governance import token_tracker
    token_tracker.print_final_report()

def run_existing_project_pipeline(routing: dict, base_workspace: str):
    """
    Runs the correct pipeline for existing project changes.
    patch  → DRAFT_CODER only
    fix    → DRAFT_CODER → LOGIC_EXPANDER → DEEP_TESTER
    rebuild → full pipeline
    """
    # Import inside function to avoid circular imports
    from agency.patching import phase_patch_draft_coder, prune_error
    from agency.orchestration import (
        phase_2b_logic_expander, phase_3_a_test_lead, 
        phase_3_b_deep_tester, run_full_pipeline
    )
    
    project_name = routing["project"]
    project_root = routing["project_root"]
    user_input = routing["user_input"]
    action = routing["action"]
    
    project_paths = {
        "root": project_root,
        "management": os.path.join(project_root, "0_Management"),
        "research": os.path.join(project_root, "1_Research"),
        "drafts": os.path.join(project_root, "2_Source_Control", "Drafts"),
        "production": os.path.join(project_root, "2_Source_Control", 
                                   "04_Production", "final_code.py"),
        "testing": os.path.join(project_root, "3_Testing")
    }
    
    PATHS["root"] = project_paths["root"]
    PATHS["testing"] = project_paths["testing"]
    PATHS["production"] = project_paths["production"]
    PATHS["draft_skeleton"] = os.path.join(project_paths["drafts"], "draft.py")
    PATHS["raw_research"] = os.path.join(project_paths["research"], "research_log.md")
    
    existing_code = read_file(project_paths["production"])
    
    briefing = {
        "project_name": project_name,
        "project": project_name,
        "task": user_input,
        "brief": user_input,
        "existing_code": existing_code,
        "mode": action,
        "complexity": "simple" if action == "patch" else "complex"
    }
    
    print(f"\n🔄 MODE: {action.upper()} — {project_name}")
    
    if action == "patch":
        print("✏️ Launching Targeted Patch System...")
        patched_code = phase_patch_draft_coder(briefing, project_paths)
        update_change_log(project_paths, user_input, action, "DRAFT_CODER", 
                         "success" if patched_code else "failed")
        
    elif action == "fix":
        print("🔧 Running targeted fix pipeline...")
        
        # Load any existing test execution logs to immediately start with historical context
        import glob
        testing_dir = project_paths["testing"]
        log_files = glob.glob(os.path.join(testing_dir, "test_execution_v*.log"))
        
        error_report = ""
        if log_files:
            def get_log_version(filepath):
                match = re.search(r'test_execution_v(\d+)\.log$', os.path.basename(filepath))
                return int(match.group(1)) if match else 0
            latest_log = max(log_files, key=get_log_version)
            print(f"📋 Found existing test execution log: {os.path.basename(latest_log)}")
            error_report = prune_error(read_file(latest_log))
        
        fix_attempt = 0
        max_fix_attempts = 3
        success = False
        
        while fix_attempt < max_fix_attempts:
            fix_attempt += 1
            print(f"\n🔄 FIX CYCLE {fix_attempt}/{max_fix_attempts}")
            
            patched = phase_patch_draft_coder(
                briefing, project_paths, 
                error_report=error_report,
                max_attempts=1
            )
            
            if not patched:
                print("❌ Patch failed — stopping fix cycle")
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
                    print(f"✅ Fix verified after {fix_attempt} attempt(s)")
                    success = True
                    update_change_log(
                        project_paths, user_input, "fix",
                        "DRAFT_CODER→LOGIC→TEST", 
                        f"SUCCESS on attempt {fix_attempt}"
                    )
                    break
                else:
                    error_report = prune_error(exec_log)
                    print(f"⚠️ Tests failed. Preparing attempt {fix_attempt + 1}...")
        
        if not success:
            update_change_log(
                project_paths, user_input, "fix",
                "DRAFT_CODER→LOGIC→TEST",
                f"FAILED after {max_fix_attempts} attempts"
            )
            print("❌ Fix pipeline exhausted. Manual review required.")
        
    elif action == "rebuild":
        print("🏗️ Full rebuild initiated...")
        run_full_pipeline(briefing, project_paths)
        update_change_log(project_paths, user_input, action, 
                         "FULL PIPELINE", "complete")

    from agency.governance import token_tracker
    token_tracker.print_final_report()
