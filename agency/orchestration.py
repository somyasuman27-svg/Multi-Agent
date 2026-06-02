import os
import re
import json
import sys
import time
from datetime import datetime
from config import PATHS, ROOT_DIR
from agency.execution import read_file, write_file, append_file, extract_handoff, append_delta_log, update_read_state
from agency.memory import inject_memory_into_prompt, update_agent_memory
from agency.testing import is_web_project, execute_in_sandbox, create_local_project_dir
from agency.governance import complexity_classifier, human_checkpoint
from agency.patching import extract_code_block
from api_bridge import call_agent

FLASK_WEB_RULES = """
CRITICAL FLASK MULTI-FILE RULES (MUST FOLLOW):
- final_code.py lives in 2_Source_Control/04_Production/
- templates/ and static/ live at the PROJECT ROOT (parent of 2_Source_Control/)
- You MUST configure Flask with explicit absolute paths:
  PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
  app = Flask(
      __name__,
      template_folder=os.path.join(PROJECT_ROOT, "templates"),
      static_folder=os.path.join(PROJECT_ROOT, "static"),
  )
- Do NOT use bare Flask(__name__) when templates/static are outside 04_Production/
- Required deliverables when applicable: final_code.py, templates/index.html, static/css/style.css, static/js/main.js, requirements.txt
- Code must pass unit tests that import final_code from 04_Production while assets sit at project root.
"""

def _tests_passed(verdict: str) -> bool:
    lowered = verdict.lower()
    return "fail" not in lowered and "error" not in lowered

def _coding_agent_instruction(base: str, project_paths: dict) -> str:
    if is_web_project(project_paths):
        return base + FLASK_WEB_RULES
    return base

def phase_2_c_post_coding_smoke_gate(project_paths: dict) -> tuple:
    """Quick validation after Phase 2 — catches broken imports/paths before test generation."""
    production = project_paths.get("production") or PATHS["production"]
    if not os.path.exists(production):
        return False, "Smoke gate: production file missing."

    if is_web_project(project_paths):
        production_dir = os.path.dirname(os.path.abspath(production))
        check_script = os.path.join(project_paths["root"], "3_Testing", "_smoke_gate_check.py")
        check_code = f'''import os
import sys
sys.path.insert(0, r"{production_dir}")
from final_code import app
app.config["TESTING"] = True
client = app.test_client()
response = client.get("/")
if response.status_code >= 400:
    print(f"SMOKE FAIL: GET / returned {{response.status_code}}")
    print(response.get_data(as_text=True)[:800])
    sys.exit(1)
css = client.get("/static/css/style.css")
if css.status_code == 404:
    print("SMOKE WARN: static/css/style.css returned 404 (check static_folder)")
print("SMOKE OK")
'''
        write_file(check_script, check_code)
        log, ok = execute_in_sandbox(check_script, cwd=project_paths.get("testing") or project_paths["root"])
        try:
            os.remove(check_script)
        except OSError:
            pass
        return ok, log

    log, ok = execute_in_sandbox(production, cwd=project_paths["root"])
    return ok, log

def _auto_fix_coding(briefing_data: dict, project_paths: dict,
                     error_report: str, max_attempts: int = 2, label: str = "fix") -> tuple:
    from agency.patching import phase_patch_draft_coder, prune_error

    trimmed = prune_error(error_report)
    for attempt in range(1, max_attempts + 1):
        print(f"\n🔧 {label.upper()} CYCLE {attempt}/{max_attempts}")
        if not phase_patch_draft_coder(briefing_data, project_paths, error_report=trimmed, max_attempts=1):
            return False, trimmed
        production = read_file(project_paths.get("production") or PATHS["production"])
        if production:
            phase_2_b_logic_expander(production, briefing_data)
        ok, log = phase_2_c_post_coding_smoke_gate(project_paths)
        if ok:
            return True, log
        trimmed = prune_error(log)
    return False, trimmed

def dequeue_completed_task(project_name: str) -> bool:
    """Remove the completed task from task_queue.json."""
    queue_path = os.path.join(ROOT_DIR, "0_Management", "task_queue.json")
    if not os.path.exists(queue_path):
        return False
    try:
        queue_data = json.loads(read_file(queue_path))
        tasks = queue_data.get("tasks", [])
        if not tasks:
            return False
        first = tasks[0]
        first_name = first.get("project") or first.get("project_name") or first.get("name")
        if first_name == project_name:
            queue_data["tasks"] = tasks[1:]
            write_file(queue_path, json.dumps(queue_data, indent=4))
            print(f"✅ Dequeued completed task: {project_name}")
            return True
    except Exception as e:
        print(f"⚠️ Could not dequeue task: {e}")
    return False

def _update_pipeline_memories(project_paths: dict, project_name: str, final_result: str, research_ok: bool):
    """Record honest outcomes — no 'success' for coders when tests failed."""
    coder_result = final_result
    research_result = "success" if research_ok else "failed"
    update_agent_memory("CEO", project_paths, project_name, "Create project plan", "success",
                        "Ensured clear roadmap definition.", "Avoid ambiguous briefs.")
    update_agent_memory("RND_COLLECTOR_1", project_paths, project_name, "Deep research specifications",
                        research_result,
                        "Gathered libraries and requirements." if research_ok else "Research API failed — used fallback.",
                        "Fix Jina API key or enable DDG fallback.")
    update_agent_memory("RND_COLLECTOR_2", project_paths, project_name, "Foundational top 5 rules",
                        research_result, "Laid down baseline code rules.", "Avoid empty research handoffs.")
    update_agent_memory("DRAFT_CODER", project_paths, project_name, "Scaffold code skeletal structure",
                        coder_result,
                        "Flask apps need explicit template_folder/static_folder at project root." if coder_result == "failed" else "Laid basic structure cleanly.",
                        "Never use bare Flask(__name__) for multi-file web projects.")
    update_agent_memory("LOGIC_EXPANDER", project_paths, project_name, "Expand logic and error handlers",
                        coder_result,
                        "Verify Flask paths before handoff." if coder_result == "failed" else "Wired logic and handlers.",
                        "Avoid skipping path validation on web projects.")
    update_agent_memory("TEST_LEAD", project_paths, project_name, "Compile automated test suite", "success",
                        "Generated automated tests cleanly.", "Avoid not mock-patching network requests.")
    update_agent_memory("DEEP_TESTER", project_paths, project_name, "Execute automated test suite",
                        final_result, f"Test verdict: {final_result}.", "Investigate 500/404 on Flask routes early.")
    update_agent_memory("ASSISTANT_MANAGER", project_paths, project_name, "Compile final completion report",
                        final_result, f"Report generated with status {final_result}.", "Avoid unchecked dependencies.")

def phase_0_briefing():
    """ 
    CEO reads the next task from the queue, creates an execution plan,
    and assigns roles. Simple tasks can skip to Phase 2.
    """
    print("\n👑 PHASE 0: CEO PLANNING")
    
    # 1. Read the task queue
    queue_path = os.path.join(ROOT_DIR, "0_Management", "task_queue.json")
    if not os.path.exists(queue_path):
        print("❌ Error: task_queue.json not found.")
        return None
    
    queue_data = json.loads(read_file(queue_path))
    if not queue_data.get("tasks"):
        print("📭 Task queue is empty.")
        return None
    
    # Pick the top task
    task = queue_data["tasks"][0]
    task_brief = task.get("brief") or task.get("project_brief") or task.get("task_brief") or ""
    project_name = task.get("project") or task.get("project_name") or task.get("name")
    
    if not project_name and task_brief:
        words = re.sub(r'[^a-zA-Z0-9\s]', '', task_brief).split()
        slug_words = [w for w in words if w.lower() not in [
            "act", "as", "an", "elite", "build", "a", "the", "using", "with", "for", "on", "serving", "development", "agency"
        ]]
        if slug_words:
            project_name = "_".join(slug_words[:3])
        else:
            project_name = "_".join(words[:3]) if words else "Auto_Generated_Project"
            
    if not project_name:
        project_name = "Auto_Project_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        
    print(f"🚀 Processing Task: {project_name}")
    
    # 2. Classify Complexity
    complexity = complexity_classifier(task_brief)
    
    # 3. Create Official Briefing
    instruction = f"""
    You are the CEO.
    Analyze this task brief for project '{project_name}'.
    Create a strict execution plan.
    1. List the files to be created/modified.
    2. Confirm the agent assignments:
       - If the project requires a web interface, web app, HTML/CSS/JS page, styling, or UI/UX design, include the ANTIGRAVITY_DESIGNER (UI/UX Team) in the coding phase to apply visual design polish (RND_COLLECTOR -> DRAFT_CODER -> LOGIC_EXPANDER -> ANTIGRAVITY_DESIGNER -> DEEP_TESTER -> ASSISTANT_MANAGER).
       - If the project is backend-only, non-web, or terminal-based, exclude ANTIGRAVITY_DESIGNER (RND_COLLECTOR -> DRAFT_CODER -> LOGIC_EXPANDER -> DEEP_TESTER -> ASSISTANT_MANAGER).
    3. Output your plan as a structured briefing.
    """
    
    print("⏳ CEO is reviewing the task...")
    task_brief_with_mem = inject_memory_into_prompt("CEO", {}, task_brief)
    full_briefing = call_agent("CEO", instruction, task_brief_with_mem)
    
    # 4. Save the plan
    briefing_output_path = os.path.join(ROOT_DIR, "0_Management", "manager_briefing_output.json")
    briefing_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "project": project_name,
        "complexity": complexity,
        "brief": task_brief,
        "plan": full_briefing,
        "status": "pending_approval"
    }
    write_file(briefing_output_path, json.dumps(briefing_data, indent=4))
    
    from agency.governance import token_tracker
    print(f"📊 Budget Status: {token_tracker.get_rate_limit_status()}")
    
    # 5. HUMAN CHECKPOINT
    if not human_checkpoint(f"CEO Execution Plan for {project_name}", full_briefing):
        print("🛑 Agency run aborted by user.")
        return None
    
    append_delta_log("CEO", "0", 1, "planned", f"Created execution plan for {project_name}", "Handoff to Phase 1/2")
    update_read_state("CEO", "0")
    
    return briefing_data

def phase_1_a_research_collection(project_brief: str):
    """
    STEP A: RND_COLLECTOR 1 & 2 search via CLI/API.
    """
    print("\n🧪 PHASE 1A: RAW DATA COLLECTION (RND TEAM)")
    
    foresight_context = ""
    queue_path = os.path.join(ROOT_DIR, "0_Management", "task_queue.json")
    if os.path.exists(queue_path):
        try:
            with open(queue_path, "r", encoding="utf-8") as f:
                queue_data = json.load(f)
            tasks = queue_data.get("tasks", [])
            if len(tasks) > 1:
                foresight_context = "\n=== UPCOMING CLIENT TASKS FORESIGHT ===\n"
                foresight_context += "The client has queued the following upcoming tasks immediately after this one:\n"
                for idx, t in enumerate(tasks[1:], 1):
                    proj_name = t.get("project") or t.get("project_name") or t.get("name") or f"Upcoming Project {idx}"
                    brief_text = t.get("brief") or t.get("project_brief") or t.get("task_brief") or ""
                    short_brief = brief_text[:500] + "..." if len(brief_text) > 500 else brief_text
                    foresight_context += f"{idx}. Project: {proj_name}\n   Brief Summary: {short_brief}\n\n"
                foresight_context += "Use this foresight to gather technical specifications and architectural structures that will make the current build highly modular, extensible, and compatible with these upcoming client requirements!\n"
        except Exception as e:
            print(f"⚠️ Failed to parse task_queue.json for foresight: {e}")

    task_file_path = os.path.join(PATHS["root"], "task.json")
    with open(task_file_path, "w", encoding="utf-8") as f:
        json.dump({"project_brief": project_brief}, f, indent=4)
    print("📁 Saved task.json into the project sandbox for agents to read.")
    
    print("📡 Dispatching RND_COLLECTOR_1 (2.5-Flash DDG Search) for Deep Architecture...")
    research_instruction_1 = f"""
    Act as a search query generator for the R&D phase.
    1. Review the provided project brief to understand the requirements.
    2. Generate a numbered list of maximum 5 specific, high-quality search queries to find modern best practices, libraries, and modular code structures for the requested stack.
    {foresight_context}
    Output MUST be a numbered list of max 5 queries. Output ONLY the queries, no extra talk or JSON.
    """
    research_instruction_1_with_mem = inject_memory_into_prompt("RND_COLLECTOR_1", PATHS, research_instruction_1)
    raw_response_1 = call_agent("RND_COLLECTOR_1", research_instruction_1_with_mem, project_brief, project_dir=PATHS["root"])
    clean_log_1 = raw_response_1.strip()

    print("📡 Dispatching RND_COLLECTOR_2 (2.5-Flash) for Comprehensive Foundation Rules...")
    research_instruction_2 = f"""
    Act as an R&D Assistant. 
    1. Review the provided project brief.
    2. Review the deep architecture research collected by RND_COLLECTOR_1 below:
    === RND_COLLECTOR_1 DATA ===
    {clean_log_1}
    ============================
    3. Based on the project brief, the RND_COLLECTOR_1 data, and the upcoming client roadmap, provide a comprehensive set of foundational rules, best practices, and architectural steps our coders must follow to build this project at the highest quality. Do not artificially limit yourself to 5 rules; provide as much detail as necessary to ensure the best possible output.
    {foresight_context}
    At the very end of your response, output ONLY this exact JSON block:
    {{
      "status": "complete",
      "handoff_to": "DRAFT_CODER",
      "trial_number": 1,
      "error_type": "none",
      "summary": "Collected comprehensive foundational rules.",
      "errors": "none",
      "checkpoint_needed": false
    }}
    """
    research_instruction_2_with_mem = inject_memory_into_prompt("RND_COLLECTOR_2", PATHS, research_instruction_2)
    raw_response_2 = call_agent("RND_COLLECTOR_2", research_instruction_2_with_mem, project_brief, project_dir=PATHS["root"])
    
    handoff = extract_handoff(raw_response_2)
    clean_log_2 = raw_response_2.split('{')[0].strip()
    
    combined_log = (
        "## PART 1: DEEP ARCHITECTURE (RND_COLLECTOR_1)\n"
        f"{clean_log_1}\n\n"
        "## PART 2: COMPREHENSIVE FOUNDATION RULES (RND_COLLECTOR_2)\n"
        f"{clean_log_2}"
    )
    
    log_path = PATHS["raw_research"]
    write_file(log_path, f"# RAW RESEARCH LOG\n\n{combined_log}")
    
    if handoff.get("status") == "failed":
        print(f"❌ Research Collection Failed: {handoff.get('errors')}")
        return handoff
    
    append_delta_log("RND_COLLECTOR", "1A", handoff.get("trial_number", 1), 
                     "complete", "Collected dual-agent research findings via CLI.", "Handoff to Phase 2 (Draft Coder)")
    update_read_state("RND_COLLECTOR", "1A")
    
    print("✅ RND Team step complete. Results saved for context injection.")
    return handoff

def phase_2_a_draft_coder(briefing_data, custom_instruction=None):
    """
    STEP 2A: DRAFT_CODER writes the initial script based on the CEO's plan.
    """
    print("\n✍️ PHASE 2A: DRAFTING CODE (DRAFT_CODER)")
    
    plan = briefing_data.get("plan", "No plan provided.")
    project = briefing_data.get("project", "unknown_project")
    
    if custom_instruction:
        instruction = custom_instruction
    else:
        instruction = _coding_agent_instruction("""
        You are the DRAFT_CODER. 
        Your job is to write the initial project code strictly based on the CEO's briefing.
        Output ALL required files using the following strict format for each file:
        ==== FILE: path/to/filename.ext ====
        ... raw code here ...
        ==== END FILE ====
        For python backend code, use 'final_code.py' as the filename.
        Do not include any conversational text, pleasantries, or explanations.
        """, PATHS)
    
    print(f"⏳ DRAFT_CODER is writing the initial code for '{project}'...")
    plan_with_mem = inject_memory_into_prompt("DRAFT_CODER", PATHS, plan)
    raw_response = call_agent("DRAFT_CODER", instruction, plan_with_mem, project_dir=PATHS["root"])
    
    from agency.patching import extract_all_files, extract_code_block
    files = extract_all_files(raw_response)
    
    if not files:
        python_code = extract_code_block(raw_response)
        files = {"final_code.py": python_code}
        
    if "### [FIX LOG]" in raw_response:
        log_part = raw_response.split("### [FIX LOG]")[1].split("###")[0].strip()
        briefing_data["latest_fix_log"] = log_part
    
    draft_path = PATHS["draft_skeleton"]
    
    python_code = ""
    for rel_path, content in files.items():
        if rel_path == "final_code.py" or rel_path == "draft.py" or rel_path.endswith("final_code.py") or rel_path.endswith("draft.py"):
            full_path = draft_path
            python_code = content
        else:
            full_path = os.path.join(PATHS["root"], rel_path)
            
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        write_file(full_path, content)
        print(f"✅ Draft saved to: {full_path}")
        
    if not python_code:
        if os.path.exists(draft_path):
            python_code = read_file(draft_path)
        elif os.path.exists(PATHS["production"]):
            python_code = read_file(PATHS["production"])
    
    append_delta_log("DRAFT_CODER", "2A", 1, "complete", f"Wrote {len(files)} initial draft files.", "Handoff to Phase 2B (Logic Expander)")
    update_read_state("DRAFT_CODER", "2A")
    
    return python_code

def phase_2_b_logic_expander(draft_code, briefing_data, custom_instruction=None):
    """
    STEP 2B: LOGIC_EXPANDER reviews the draft, adds best practices, and finalizes logic.
    """
    print("\n🧠 PHASE 2B: LOGIC EXPANSION (LOGIC_EXPANDER)")
    
    plan = briefing_data.get("plan", "No plan provided.")
    
    if custom_instruction:
        instruction = custom_instruction
    else:
        instruction = _coding_agent_instruction("""
        You are the LOGIC_EXPANDER.
        Review the provided draft code and the original CEO plan.
        Improve the code by adding proper error handling, professional best practices (e.g., if __name__ == '__main__':), and clean comments.
        VERIFY Flask template_folder/static_folder point to project root when this is a web project.
        Output ALL finalized files using the following strict format for each file:
        ==== FILE: path/to/filename.ext ====
        ... raw code here ...
        ==== END FILE ====
        For the main python backend, use 'final_code.py' as the filename.
        Do not include any conversational text.
        """, PATHS)
    
    prompt = f"=== CEO PLAN ===\n{plan}\n\n=== CURRENT DRAFT ===\n{draft_code}"
    
    print("⏳ LOGIC_EXPANDER is reviewing and upgrading the code...")
    prompt_with_mem = inject_memory_into_prompt("LOGIC_EXPANDER", PATHS, prompt)
    raw_response = call_agent("LOGIC_EXPANDER", instruction, prompt_with_mem, project_dir=PATHS["root"])
    
    from agency.patching import extract_all_files, extract_code_block
    files = extract_all_files(raw_response)
    
    if not files:
        python_code = extract_code_block(raw_response)
        files = {"final_code.py": python_code}
        
    prod_path = PATHS["production"]
    
    final_code = ""
    for rel_path, content in files.items():
        if rel_path == "final_code.py" or rel_path == "draft.py" or rel_path.endswith("final_code.py") or rel_path.endswith("draft.py"):
            full_path = prod_path
            final_code = content
        else:
            full_path = os.path.join(PATHS["root"], rel_path)
            
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        write_file(full_path, content)
        print(f"✅ Final upgraded code saved to: {full_path}")
    
    if not final_code and os.path.exists(prod_path):
        final_code = read_file(prod_path)
        
    append_delta_log("LOGIC_EXPANDER", "2B", 1, "complete", f"Expanded logic for {len(files)} files.", "Handoff to Phase 3 (Deep Tester)")
    update_read_state("LOGIC_EXPANDER", "2B")
    
    return final_code

def phase_3_a_test_lead(briefing_data):
    """
    STEP 3A: TEST_LEAD executes a smoke test, reviews execution logs,
    and compiles a robust python test suite.
    """
    print("\n📡 PHASE 3A: SMOKE TESTING & TEST CASE CREATION (TEST_LEAD)")
    
    plan = briefing_data.get("plan", "No plan provided.")
    project = briefing_data.get("project", "unknown_project")
    
    is_web = is_web_project(PATHS)
    
    if is_web:
        print("⏳ Executing smoke test in sandbox (Web Server)...")
        import time
        server_proc = subprocess_popen_safe(PATHS["production"])
        time.sleep(4)
        if server_proc.poll() is None:
            smoke_log = "Server started successfully"
            is_booted = True
        else:
            smoke_log = server_proc.stderr.read().decode()
            is_booted = False
        server_proc.terminate()
        server_proc.wait()
    else:
        print("⏳ Executing smoke test in sandbox (Standard Script)...")
        smoke_log, is_booted = execute_in_sandbox(PATHS["production"], cwd=PATHS["root"])
    
    import glob
    test_dir = PATHS["testing"]
    existing_tests_pattern = os.path.join(test_dir, "test_suite_v*.py")
    existing_test_files = glob.glob(existing_tests_pattern)
    
    def _extract_test_summary(filepath):
        """Token-saving helper: extracts only test function names to avoid context explosion."""
        try:
            content = read_file(filepath)
            if not content:
                return "Empty test file."
            funcs = re.findall(r'def\s+(test_[a-zA-Z0-9_]+)\(', content)
            if funcs:
                return f"Contains test functions: {', '.join(funcs[:25])}" + (f" (and {len(funcs)-25} more)" if len(funcs) > 25 else "")
            return "No test functions found."
        except Exception as e:
            return f"Could not summarize: {e}"

    next_ver = 1
    previous_tests_context = "No previous test cases exist."
    
    if existing_test_files:
        version_numbers = []
        for f in existing_test_files:
            match = re.search(r'test_suite_v(\d+)\.py$', os.path.basename(f))
            if match:
                version_numbers.append(int(match.group(1)))
        if version_numbers:
            next_ver = max(version_numbers) + 1
            
        previous_tests_context = "Existing test cases already implemented (do NOT replicate these; build new cases instead):\n\n"
        def get_version(filepath):
            match = re.search(r'test_suite_v(\d+)\.py$', os.path.basename(filepath))
            return int(match.group(1)) if match else 0
            
        sorted_files = sorted(existing_test_files, key=get_version)
        for f in sorted_files:
            summary = _extract_test_summary(f)
            previous_tests_context += f"--- {os.path.basename(f)} ---\n{summary}\n\n"
            
    print(f"📁 Versioning test cases. Preparing test_suite_v{next_ver}...")
    
    instruction = f"""
    You are the TEST_LEAD.
    Analyze the project plan, original CEO briefing, smoke test logs, and all past test cases that have already been designed.
    
    Your goal is to build upon the existing test cases by creating a brand-new, unique automated Python test script (test_suite_v{next_ver}.py) that tests additional scenarios, edge cases, and modules without overwriting or repeating past cases.
    
    CRITICAL TECHNICAL REQUIREMENT: For Flask/web-based projects, the unit test script (test_suite_v{next_ver}.py) MUST use Flask's native test client (app.test_client()) to test routes and HTML contents. To import the app cleanly, you MUST first dynamically add the production zone to the Python path at the top of your script using:
    ```python
    import sys
    import os
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    sys.path.append(os.path.join(PROJECT_ROOT, "2_Source_Control", "04_Production"))
    from final_code import app
    ```
    Do NOT start the server or make live HTTP/requests calls to localhost:5000 in your unit tests, as the server is not running during the isolated unit testing stage.
    
    CRITICAL EXECUTION REQUIREMENT: The automated Python test script (test_suite_v{next_ver}.py) MUST include a standard execution entry point block at the very end of the file.
    If you are writing the tests as a pytest suite (using 'test_' prefixed functions), append this EXACT block to the end of the file:
    ```python
    if __name__ == '__main__':
        import pytest
        import sys
        sys.exit(pytest.main([__file__]))
    ```
    If you are writing the tests as a unittest suite, append:
    ```python
    if __name__ == '__main__':
        import unittest
        unittest.main()
    ```
    
    {"Additionally, since this is a WEB-based project, you MUST also generate a secondary, separate Playwright browser test script (browser_tests_v" + str(next_ver) + ".py) using headless sync Playwright. The browser test script MUST follow the Playwright browser test template precisely (import sync_playwright, test HTTP 200, test page title, check for console errors, and any specific interaction checks based on the task description)." if is_web else ""}
    
    Output format:
    1. Smoke Test & Readiness Report (markdown)
    2. Automated Python test script enclosed STRICTLY in a markdown ```python block.
    {"3. Playwright browser test script enclosed STRICTLY in a secondary markdown ```python block." if is_web else ""}
    Ensure all python blocks are completely valid and runnable.
    """
    
    production_code = read_file(PATHS["production"])
    code_context = f"=== PYTHON SERVER CODE ===\n{production_code}\n\n"
    
    if is_web:
        # Check standard locations for index.html
        html_locations = [
            os.path.join(PATHS["root"], "templates", "index.html"),
            os.path.join(os.path.dirname(PATHS["production"]), "templates", "index.html"),
            os.path.join(PATHS["root"], "2_Source_Control", "04_Production", "templates", "index.html")
        ]
        for html_path in html_locations:
            if os.path.exists(html_path):
                code_context += f"=== FRONTEND CODE (index.html) ===\n{read_file(html_path)}\n\n"
                break

    prompt = f"=== CEO PLAN ===\n{plan}\n\n{code_context}=== SMOKE TEST RUN SUCCESS: {is_booted} ===\n=== SMOKE TEST LOG ===\n{smoke_log}\n\n=== PREVIOUS TEST CASES ===\n{previous_tests_context}"
    
    print("⏳ TEST_LEAD is compiling the test cases...")
    prompt_with_mem = inject_memory_into_prompt("TEST_LEAD", PATHS, prompt)
    raw_response = call_agent("TEST_LEAD", instruction, prompt_with_mem, project_dir=PATHS["root"])
    
    pattern = r"```(?:python|py)?\s*\n(.*?)\n```"
    code_blocks = re.findall(pattern, raw_response, re.DOTALL | re.IGNORECASE)
    
    test_code = code_blocks[0].strip() if len(code_blocks) > 0 else extract_code_block(raw_response)
    
    # Strip any existing __main__ block to ensure our standardized, bulletproof execution block is used
    test_code = re.sub(r'if __name__\s*==\s*[\'"]__main__[\'"]\s*:\s*.*$', '', test_code, flags=re.DOTALL).strip()
    
    # Bulletproof safeguard: automatically append execution entry point block if missing
    if "if __name__" not in test_code:
        if "pytest" in test_code or "def test_" in test_code:
            test_code += "\n\nif __name__ == '__main__':\n    import pytest\n    import sys\n    # Pytest requires .py files for collection and execution\n    target_file = __file__.replace('.pyc', '.py') if __file__.endswith('.pyc') else __file__\n    sys.exit(pytest.main([target_file]))\n"
        elif "unittest" in test_code:
            test_code += "\n\nif __name__ == '__main__':\n    import unittest\n    unittest.main()\n"
            
    import py_compile
    test_src_path = os.path.join(test_dir, f"test_suite_v{next_ver}.py")
    compiled_test_path = os.path.join(test_dir, f"test_suite_v{next_ver}.pyc")
    
    write_file(test_src_path, test_code)
    print(f"📦 Compiling automated test script into binary bytecode (.pyc) for token-saving...")
    py_compile.compile(test_src_path, cfile=compiled_test_path)
    
    print(f"✅ Pre-compiled bytecode saved successfully to: {compiled_test_path}")
    
    if is_web:
        browser_code = ""
        if len(code_blocks) >= 2:
            browser_code = code_blocks[1].strip()
        else:
            browser_code = f"""from playwright.sync_api import sync_playwright
import sys

def run_browser_tests(base_url="http://localhost:5000"):
    results = []
    errors = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) 
                if msg.type == "error" else None)
        
        try:
            response = page.goto(base_url, timeout=10000)
            if response.status == 200:
                results.append("✅ HTTP 200 — Page loaded successfully")
            else:
                errors.append(f"❌ HTTP {{response.status}} — Page failed to load")
            
            title = page.title()
            if title:
                results.append(f"✅ Page title: {{title}}")
            else:
                errors.append("❌ No page title found")
            
            page.wait_for_timeout(2000)
            if not console_errors:
                results.append("✅ No console errors detected")
            else:
                errors.append(f"❌ Console errors: {{console_errors[:3]}}")
            
        except Exception as e:
            errors.append(f"❌ Browser test crashed: {{str(e)}}")
        finally:
            browser.close()
    
    print("=" * 50)
    print("BROWSER TEST RESULTS")
    print("=" * 50)
    for r in results:
        print(r)
    for e in errors:
        print(e)
    print("=" * 50)
    print(f"PASSED: {{len(results)}} | FAILED: {{len(errors)}}")
    
    return len(errors) == 0

if __name__ == "__main__":
    success = run_browser_tests()
    sys.exit(0 if success else 1)
"""
        if "if __name__" not in browser_code:
            if "pytest" in browser_code or "def test_" in browser_code:
                browser_code += "\n\nif __name__ == '__main__':\n    import pytest\n    import sys\n    sys.exit(pytest.main([__file__]))\n"
            elif "unittest" in browser_code:
                browser_code += "\n\nif __name__ == '__main__':\n    import unittest\n    unittest.main()\n"
                
        browser_test_path = os.path.join(test_dir, f"browser_tests_v{next_ver}.py")
        write_file(browser_test_path, browser_code)
        print(f"🌐 Playwright browser test script saved to: {browser_test_path}")
        
    append_delta_log("TEST_LEAD", "3A", 1, "complete", f"Executed smoke test and compiled versioned binary test suite v{next_ver} (.pyc).", "Handoff to Phase 3B (Deep Tester)")
    update_read_state("TEST_LEAD", "3A")
    
    smoke_report = raw_response.split("```")[0].strip()
    return compiled_test_path, smoke_report

def phase_3_b_deep_tester(compiled_test_path, briefing_data, project_paths=None):
    """
    STEP 3B: DEEP_TESTER executes the pre-compiled bytecode test suite (.pyc) directly,
    analyzes the native execution logs, and outputs a final testing verdict.
    """
    print("\n🔬 PHASE 3B: DEEP TESTING & LOG VERDICT (DEEP_TESTER)")
    if project_paths is None:
        project_paths = PATHS
        
    testing_path = project_paths["testing"]
    production_path = project_paths["production"]
    
    plan = briefing_data.get("plan", "No plan provided.")
    
    match = re.search(r'_v(\d+)\.pyc$', compiled_test_path)
    ver = match.group(1) if match else "1"
    
    full_log = ""
    
    print("🧪 Running unit tests...")
    if not os.path.exists(compiled_test_path):
        # Fallback to source .py file if compiled .pyc is not found
        source_py_path = compiled_test_path.replace(".pyc", ".py")
        if os.path.exists(source_py_path):
            print(f"⚠️ Pre-compiled bytecode missing. Falling back to source Python test suite: {source_py_path}")
            compiled_test_path = source_py_path

    unit_log, unit_pass = execute_in_sandbox(compiled_test_path, cwd=testing_path)
    full_log += f"=== UNIT TESTS ===\n{unit_log}\n\n"
    
    browser_pass = True
    browser_test_path = os.path.join(
        testing_path, f"browser_tests_v{ver}.py"
    )
    
    if is_web_project(project_paths) and os.path.exists(browser_test_path):
        print("🌐 Running Playwright browser tests...")
        
        server_proc = subprocess_popen_safe(production_path)
        time.sleep(3)
        
        try:
            browser_log, browser_pass = execute_in_sandbox(
                browser_test_path, 
                cwd=testing_path
            )
            full_log += f"=== BROWSER TESTS ===\n{browser_log}\n\n"
        finally:
            server_proc.terminate()
            server_proc.wait()
    else:
        full_log += "=== BROWSER TESTS ===\nNot applicable (non-web project)\n\n"
    
    log_path = os.path.join(testing_path, f"test_execution_v{ver}.log")
    write_file(log_path, full_log)
    print(f"📋 Test log saved: test_execution_v{ver}.log")
    
    instruction = """
    You are the DEEP_TESTER.
    Review the execution output logs of the pre-compiled automated test suite.
    Did the tests execute and pass successfully?
    Output a clear summary of which tests succeeded, which failed, and a final testing verdict.
    Do not rewrite or modify any code.
    """
    
    production_code = read_file(PATHS["production"])
    code_context = f"=== PYTHON SERVER CODE ===\n{production_code}\n\n"
    if is_web_project(project_paths):
        html_locations = [
            os.path.join(PATHS["root"], "templates", "index.html"),
            os.path.join(os.path.dirname(PATHS["production"]), "templates", "index.html"),
            os.path.join(PATHS["root"], "2_Source_Control", "04_Production", "templates", "index.html")
        ]
        for html_path in html_locations:
            if os.path.exists(html_path):
                code_context += f"=== FRONTEND CODE (index.html) ===\n{read_file(html_path)}\n\n"
                break

    prompt = f"=== CEO PLAN ===\n{plan}\n\n{code_context}=== BINARY SUITE EXECUTION LOG ===\n{full_log}"
    
    print("⏳ DEEP_TESTER is reviewing execution output logs...")
    prompt_with_mem = inject_memory_into_prompt("DEEP_TESTER", project_paths, prompt)
    verdict = call_agent("DEEP_TESTER", instruction, prompt_with_mem, project_dir=project_paths["root"])
    
    verdict_file_path = os.path.join(testing_path, f"test_verdict_v{ver}.md")
    write_file(verdict_file_path, verdict)
    print(f"📝 Test verdict saved to: {verdict_file_path}")
    
    print(f"✅ Deep Testing Complete. Verdict: {verdict[:150]}...")
    
    append_delta_log("DEEP_TESTER", "3B", 1, "complete", f"Executed bytecode test suite v{ver} and saved versioned logs/verdict.", "Handoff to Phase 3C (Assistant Manager)")
    update_read_state("DEEP_TESTER", "3B")
    
    return full_log, verdict

def phase_3_c_assistant_manager(briefing_data, execution_log, test_analysis):
    """
    STEP 3C: ASSISTANT_MANAGER compiles the final delivery report.
    """
    print("\n📋 PHASE 3C: FINAL REPORT (ASSISTANT_MANAGER)")
    
    project = briefing_data.get("project", "unknown_project")
    
    instruction = """
    You are the ASSISTANT_MANAGER.
    Write a brief, professional Project Completion Report for the CEO.
    Include:
    1. Project Name
    2. Execution Status (Success/Fail based on test analysis)
    3. Terminal Output snippet (Proof of life from deep testing logs)
    If a "BUG FIX & LINE CORRECTION LEDGER" is provided, you MUST include a summary of it at the very top of your report to show the exact fixes and lines corrected.
    Output in clean Markdown.
    """
    
    ledger_str = ""
    if "lines_fixed_ledger" in briefing_data:
        ledger_str = "\n=== BUG FIX & LINE CORRECTION LEDGER ===\n" + "\n".join(briefing_data["lines_fixed_ledger"]) + "\n\n"
    
    prompt = f"=== PROJECT ===\n{project}\n{ledger_str}=== TEST VERDICT ===\n{test_analysis}\n\n=== RAW LOG ===\n{execution_log}"
    
    print("⏳ ASSISTANT_MANAGER is compiling the final report...")
    prompt_with_mem = inject_memory_into_prompt("ASSISTANT_MANAGER", PATHS, prompt)
    report = call_agent("ASSISTANT_MANAGER", instruction, prompt_with_mem, project_dir=PATHS["root"])
    
    local_mgmt_dir = os.path.join(PATHS["root"], "0_Management")
    report_path = os.path.join(local_mgmt_dir, "final_delivery_report.md")
    write_file(report_path, report)
    
    global_report_path = os.path.join(ROOT_DIR, "0_Management", "final_delivery_report.md")
    write_file(global_report_path, report)
    
    print(f"✅ Local Final Report saved to: {report_path}")
    print(f"✅ Global Final Report saved to: {global_report_path}")
    
    append_delta_log("ASSISTANT_MANAGER", "3C", 1, "complete", "Compiled final delivery report.", "PIPELINE FINISHED")
    update_read_state("ASSISTANT_MANAGER", "3C")
    
    return report

def save_localized_markdown_log(project_name: str, final_report_content: str):
    management_dir = os.path.join(ROOT_DIR, "0_Management", "Project_Logs")
    os.makedirs(management_dir, exist_ok=True)
    
    log_file = os.path.join(management_dir, f"{project_name}_execution_history.md")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    localized_content = f"""# Project Run History Snapshot: {project_name}
*Generated at: {timestamp}*

{final_report_content}
---
"""
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(localized_content)
    print(f"📝 Localized markdown history saved to: {log_file}")

def update_cross_project_memory(project_name: str, brief: str, status: str, clean_architecture_summary: str):
    memory_dir = os.path.join(ROOT_DIR, "0_Management", "Cross_Project_Memory")
    os.makedirs(memory_dir, exist_ok=True)
    
    ledger_path = os.path.join(memory_dir, "global_learning_ledger.md")
    timestamp = datetime.now().strftime("%Y-%m-%d")
    
    ledger_entry = f"""
### 🧠 Entry: {project_name} ({timestamp})
* **Initial Brief:** {brief}
* **Pipeline Build Status:** {status.upper()}
* **Proven Architectural Strategy / Lessons Learned:**
{clean_architecture_summary}

---
"""
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(ledger_entry)
    print("✨ Shared cross-project knowledge ledger successfully updated with new optimizations.")

def phase_2b_logic_expander(briefing_data, project_paths):
    """Fix-flow wrapper: runs logic expander on current production code after a patch."""
    global PATHS
    PATHS["root"] = project_paths["root"]
    production_file = project_paths.get("production") or PATHS["production"]
    existing = read_file(production_file)
    if not existing:
        print("⚠️ No production code to expand.")
        return False
    result = phase_2_b_logic_expander(existing, briefing_data)
    return bool(result)

def run_full_pipeline(briefing_data, project_paths):
    """Executes the full pipeline for a project run."""
    global PATHS
    PATHS["root"] = project_paths["root"]
    PATHS["testing"] = project_paths.get("testing") or project_paths.get("3_testing")
    PATHS["production"] = project_paths.get("production") or os.path.join(project_paths["root"], "2_Source_Control/04_Production/final_code.py")
    PATHS["draft_skeleton"] = project_paths.get("draft_skeleton") or os.path.join(project_paths.get("drafts") or os.path.join(project_paths["root"], "2_Source_Control/Drafts"), "draft.py")
    PATHS["raw_research"] = project_paths.get("raw_research") or os.path.join(project_paths.get("research") or os.path.join(project_paths["root"], "1_Research"), "research_log.md")
    
    complexity = briefing_data.get("complexity", "complex")
    project_name = briefing_data.get("project_name") or briefing_data.get("project") or "Auto_Generated_Task"
    actual_brief = briefing_data.get("brief") or briefing_data.get("task") or "No brief found"
    research_ok = True
    
    if complexity == "complex":
        print("\n[!] Task is COMPLEX. Executing Phase 1 (Research)...")
        phase_1_a_research_collection(actual_brief)
        research_log = read_file(PATHS["raw_research"])
        research_ok = "ERROR:" not in research_log or "PART 2:" in research_log
    else:
        print("\n[!] Task is SIMPLE. Bypassing Phase 1 Research.")
        
    draft = phase_2_a_draft_coder(briefing_data)
    if not draft:
        from agency.governance import token_tracker
        token_tracker.print_final_report()
        return

    final_code = phase_2_b_logic_expander(draft, briefing_data)
    if not final_code:
        from agency.governance import token_tracker
        token_tracker.print_final_report()
        return

    # Trigger UI/UX designer if it is a web project to apply premium styling and polish
    if is_web_project(project_paths):
        print("\n🎨 Web project detected — triggering UI/UX designer pipeline...")
        from agency.triage import run_uiux_pipeline
        # Ensure task is populated in the briefing data
        briefing_data["task"] = briefing_data.get("task") or actual_brief
        run_uiux_pipeline(briefing_data, project_paths)

    smoke_ok, smoke_log = phase_2_c_post_coding_smoke_gate(project_paths)
    if not smoke_ok:
        print("⚠️ Post-coding smoke gate failed — attempting auto-fix...")
        briefing_data["task"] = briefing_data.get("task") or actual_brief
        smoke_ok, smoke_log = _auto_fix_coding(briefing_data, project_paths, smoke_log, max_attempts=2, label="smoke")
        if not smoke_ok:
            print("⚠️ Smoke gate still failing — proceeding to full test suite.")

    compiled_test_path, smoke_report = phase_3_a_test_lead(briefing_data)
    if not compiled_test_path:
        from agency.governance import token_tracker
        token_tracker.print_final_report()
        return

    test_exec_log, deep_verdict = phase_3_b_deep_tester(compiled_test_path, briefing_data, project_paths)
    final_result = "success" if _tests_passed(deep_verdict) else "failed"

    fix_attempt = 0
    max_fix_attempts = 3
    while final_result == "failed" and fix_attempt < max_fix_attempts:
        fix_attempt += 1
        print(f"\n🔄 TEST FIX CYCLE {fix_attempt}/{max_fix_attempts}")
        from agency.patching import phase_patch_draft_coder, prune_error
        briefing_data["task"] = briefing_data.get("task") or actual_brief
        if not phase_patch_draft_coder(briefing_data, project_paths, error_report=prune_error(test_exec_log), max_attempts=1):
            break
        phase_2b_logic_expander(briefing_data, project_paths)
        compiled_test_path, _ = phase_3_a_test_lead(briefing_data)
        if not compiled_test_path:
            break
        test_exec_log, deep_verdict = phase_3_b_deep_tester(compiled_test_path, briefing_data, project_paths)
        final_result = "success" if _tests_passed(deep_verdict) else "failed"

    report = phase_3_c_assistant_manager(briefing_data, test_exec_log, deep_verdict)
    _update_pipeline_memories(project_paths, project_name, final_result, research_ok)

    save_localized_markdown_log(project_name, report)
    update_cross_project_memory(
        project_name=project_name,
        brief=actual_brief,
        status=final_result,
        clean_architecture_summary=(
            "Pipeline completed and tests passed."
            if final_result == "success"
            else "Tests failed — Flask path wiring and static/template folders are common root causes."
        ),
    )
    if final_result == "success":
        dequeue_completed_task(project_name)

    from agency.governance import token_tracker
    token_tracker.print_final_report()

def subprocess_popen_safe(file_path):
    """Helper to launch a subprocess securely without shell=True."""
    import subprocess
    import sys
    return subprocess.Popen(
        [sys.executable, file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
