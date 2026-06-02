import os
import re
import sys
import time
import tempfile
import shutil
import subprocess
from config import PATHS, ROOT_DIR, TIMEOUT_SECONDS, APPROVED_PACKAGES
from agency.execution import read_file, write_file

def is_web_project(project_paths: dict) -> bool:
    """
    Ollama-powered web project detector.
    Checks production code for web framework signatures.
    """
    production_path = project_paths.get("production", "")
    final_code = read_file(production_path) if production_path else ""
    
    root_path = project_paths.get("root", "")
    req_path = os.path.join(root_path, "requirements.txt") if root_path else ""
    requirements = read_file(req_path) if req_path else ""
    
    web_signals = ["flask", "django", "fastapi", "socketio", 
                   "render_template", "app.route", "uvicorn"]
    
    combined = (final_code + requirements).lower()
    detected = any(signal in combined for signal in web_signals)
    
    if detected:
        print("🌐 Web project detected — Playwright browser tests activated")
    else:
        print("🖥️ Non-web project — Standard unit tests only")
    
    return detected

def check_playwright_available() -> bool:
    """Checks if Playwright is installed and Chromium is available."""
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        print("⚠️ Playwright not installed. Run: pip install playwright && playwright install chromium")
        return False

def create_local_project_dir(project_name, base_workspace=None):
    """Creates an isolated local directory for the project."""
    if base_workspace is None:
        base_workspace = os.path.join(ROOT_DIR, "Active_Projects")
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', project_name.strip())
    project_root = os.path.join(base_workspace, safe_name)
    
    hierarchy = [
        "0_Management", "1_Research", "2_Source_Control/Drafts", 
        "3_Testing", "2_Source_Control/04_Production"
    ]
    
    os.makedirs(project_root, exist_ok=True)
    project_paths = {"root": project_root}
    
    for folder in hierarchy:
        folder_path = os.path.join(project_root, folder)
        os.makedirs(folder_path, exist_ok=True)
        key_name = folder.split('/')[-1].lower()
        project_paths[key_name] = folder_path
        
    # Auto-create local agent memory directory
    local_mem_dir = os.path.join(project_root, "0_Management", "local_agent_memory")
    os.makedirs(local_mem_dir, exist_ok=True)
    roles = ["brain", "draft_coder", "logic_expander", "deep_tester", "test_lead", "assistant_manager", "ollama"]
    for role in roles:
        role_file = os.path.join(local_mem_dir, f"{role}_memory.md")
        if not os.path.exists(role_file):
            with open(role_file, "w", encoding="utf-8") as f:
                f.write(f"# Local Agent Memory - {role.upper()}\n---\n")

    # Auto-create team-specific issue logs for Antigravity CLI triage
    mgmt_dir = os.path.join(project_root, "0_Management")
    for log_name in ["rnd_issues.log", "uiux_issues.log"]:
        log_path = os.path.join(mgmt_dir, log_name)
        if not os.path.exists(log_path):
            dept = "RnD (Code Team)" if "rnd" in log_name else "UI/UX (Design Team)"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"# {dept} Issue Log\n# Auto-created by Antigravity CLI\n---\n")
        
    return project_paths

def execute_in_sandbox(script_path, cwd=None):
    """Executes code, intercepts missing packages, auto-installs, and handles execution timeouts."""
    from agency.execution import log_langfuse_event
    start_time = time.time()
    
    if cwd is None:
        cwd = os.path.dirname(os.path.abspath(script_path)) if script_path else None
    max_attempts = 3
    for attempt in range(max_attempts):
        print(f"🔬 Sandbox Execution (Attempt {attempt + 1}/{max_attempts})...")
        try:
            result = subprocess.run(
                [sys.executable, script_path], 
                capture_output=True, 
                text=True,
                timeout=15,
                cwd=cwd
            )
            
            if result.returncode == 0:
                elapsed = time.time() - start_time
                combined_output = (result.stdout + "\n" + result.stderr).strip()
                log_langfuse_event(
                    name="execute_in_sandbox",
                    metadata={
                        "script_path": script_path,
                        "duration_sec": elapsed,
                        "success": True,
                        "output_preview": combined_output[:200]
                    }
                )
                return combined_output, True
                
            stderr_output = result.stderr
            match = re.search(r"ModuleNotFoundError:\s+No\s+module\s+named\s+'([^']+)'", stderr_output)
            
            if match:
                missing_module = match.group(1)
                normalized_module = missing_module.replace("_", "-").lower()
                approved_names = [pkg.lower() for pkg in APPROVED_PACKAGES]
                
                if normalized_module in approved_names or missing_module.lower() in approved_names:
                    print(f"📦 Intercepted missing dependency: '{missing_module}'. Whitelisted. Installing...")
                    subprocess.run([sys.executable, "-m", "pip", "install", missing_module], capture_output=True)
                    time.sleep(2)
                    continue
                else:
                    security_msg = f"❌ SECURITY WARNING: Blocked installation of unapproved package '{missing_module}'."
                    print(security_msg)
                    elapsed = time.time() - start_time
                    log_langfuse_event(
                        name="execute_in_sandbox",
                        metadata={
                            "script_path": script_path,
                            "duration_sec": elapsed,
                            "success": False,
                            "error": security_msg
                        },
                        level="ERROR"
                    )
                    # Return both the warning and the actual traceback so the agent can debug which line threw it
                    return f"{security_msg}\n{stderr_output}", False
                
            elapsed = time.time() - start_time
            log_langfuse_event(
                name="execute_in_sandbox",
                metadata={
                    "script_path": script_path,
                    "duration_sec": elapsed,
                    "success": False,
                    "error": stderr_output[:500]
                },
                level="ERROR"
            )
            return stderr_output, False
            
        except subprocess.TimeoutExpired as e:
            timeout_val = e.timeout
            print(f"⏳ Process hit timeout ({timeout_val}s). Script failed to finish in time.")
            elapsed = time.time() - start_time
            log_langfuse_event(
                name="execute_in_sandbox",
                metadata={
                    "script_path": script_path,
                    "duration_sec": elapsed,
                    "success": False,
                    "error": "TimeoutExpired"
                },
                level="ERROR"
            )
            return f"Error: Process timed out after {timeout_val} seconds.", False
            
    return "Error: Dependency resolution loop detected.", False

def run_tests_safe(test_script: str, project_path: str) -> str:
    """
    Runs test cases in an isolated temp directory.
    Strictly follows: shell=False, timeout=60, isolated subprocess.
    """
    # We copy the project files to a temp directory to prevent local writes
    with tempfile.TemporaryDirectory() as tmp:
        # Recursively copy project files to temp
        shutil.copytree(project_path, tmp, dirs_exist_ok=True)
        
        try:
            # Execute the test script using the local python environment
            # shell=False is mandatory for security
            result = subprocess.run(
                [sys.executable, test_script],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                shell=False
            )
            return (result.stdout + "\n" + result.stderr).strip()
            
        except subprocess.TimeoutExpired:
            return f"❌ ERROR: Test subprocess timed out after {TIMEOUT_SECONDS} seconds."
        except Exception as e:
            return f"❌ Subprocess Exception: {str(e)}"
