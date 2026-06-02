import os
import re
import ast
from config import PATHS
from agency.execution import read_file, write_file, append_file
from agency.memory import inject_memory_into_prompt
from api_bridge import call_agent

def prune_error(error_text: str, max_lines: int = 50) -> str:
    """Prunes long error logs or stack traces to save tokens."""
    if not error_text:
        return "none"
    lines = error_text.strip().splitlines()
    if len(lines) <= max_lines:
        return error_text
    return "\n".join(lines[:max_lines]) + f"\n\n... [Truncated {len(lines) - max_lines} lines]"

def extract_code_block(text: str, lang: str = "python") -> str:
    """Extracts raw code from markdown blocks."""
    pattern = rf"```{lang}\s*\n(.*?)\n```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
        
    # Try generic code block if lang-specific one fails
    pattern_generic = r"```(?:[a-zA-Z0-9_-]+)?\s*\n(.*?)\n```"
    match_generic = re.search(pattern_generic, text, re.DOTALL | re.IGNORECASE)
    if match_generic:
        return match_generic.group(1).strip()
        
    return text.replace("```python", "").replace("```", "").strip()

def extract_all_files(text: str) -> dict:
    """
    Extracts multiple files from the text using the ==== FILE: ... ==== format.
    Returns a dictionary mapping filenames to their code content.
    """
    files = {}
    pattern = r'====\s*FILE:\s*([^\n=]+)\s*====\s*(.*?)\s*====\s*END FILE\s*===='
    matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)
    for match in matches:
        filename = match.group(1).strip()
        content = match.group(2).strip()
        files[filename] = content
    return files

def extract_function_block(filepath: str, function_name: str) -> str:
    """
    Extracts the complete source code of a specific function from a file.
    Uses AST parsing for reliability — not regex.
    Returns empty string if function not found.
    """
    source = read_file(filepath)
    if not source:
        return ""
    
    try:
        tree = ast.parse(source)
        lines = source.splitlines(keepends=True)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == function_name:
                    start_line = node.lineno - 1
                    end_line = node.end_lineno
                    func_lines = lines[start_line:end_line]
                    return "".join(func_lines)
        return ""
    except SyntaxError as e:
        print(f"⚠️ AST parse error in {filepath}: {e}. Trying regex fallback...")
        lines = source.splitlines(keepends=True)
        pattern = rf"^\s*def\s+{function_name}\b"
        start_line = -1
        for i, line in enumerate(lines):
            if re.match(pattern, line):
                start_line = i
                break
        if start_line == -1:
            return ""
        indent_match = re.match(r"^(\s*)", lines[start_line])
        indent = indent_match.group(1) if indent_match else ""
        func_lines = [lines[start_line]]
        for line in lines[start_line + 1:]:
            if not line.strip() or line.startswith(indent + " ") or line.startswith(indent + "\t"):
                func_lines.append(line)
            else:
                break
        return "".join(func_lines)

def apply_function_patch(filepath: str, function_name: str, 
                          new_function_code: str) -> bool:
    """
    Replaces a specific function in a file with new code.
    Uses AST to find exact location.
    """
    from agency.execution import log_langfuse_event
    source = read_file(filepath)
    if not source:
        print(f"❌ File not found: {filepath}")
        return False
    
    try:
        tree = ast.parse(source)
        lines = source.splitlines(keepends=True)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == function_name:
                    start_line = node.lineno - 1
                    end_line = node.end_lineno
                    
                    before = "".join(lines[:start_line])
                    after = "".join(lines[end_line:])
                    
                    if not new_function_code.endswith('\n'):
                        new_function_code += '\n'
                    
                    patched_source = before + new_function_code + after
                    write_file(filepath, patched_source)
                    
                    print(f"✅ Patched {function_name}() successfully")
                    print(f"   Lines replaced: {start_line+1} to {end_line}")
                    
                    # Log to Langfuse
                    log_langfuse_event(
                        name="apply_function_patch",
                        metadata={
                            "filepath": filepath,
                            "function_name": function_name,
                            "lines_changed": len(new_function_code.splitlines())
                        }
                    )
                    return True
        print(f"❌ Function '{function_name}' not found in {filepath}")
        return False
    except SyntaxError as e:
        print(f"❌ Syntax error — patch not applied: {e}")
        return False

def identify_broken_functions(error_report: str, filepath: str) -> list:
    """
    Parses DEEP_TESTER error report to identify broken function names.
    Cross-references with actual functions in the file.
    """
    broken_functions = []
    
    # Pattern 1 — Python traceback format
    traceback_pattern = r'in (\w+)\s*$'
    matches = re.findall(traceback_pattern, error_report, re.MULTILINE)
    broken_functions.extend(matches)
    
    # Pattern 2 — Test failure format  
    test_pattern = r'\b(test_\w+)\b'
    test_matches = re.findall(test_pattern, error_report)
    
    # Standard route mappings from test name signatures to production functions
    route_map = {
        "home_page": "index",
        "menu_page": "menu",
        "reservation_page": "reservation",
        "reserve_page": "reservation",
        "membership_page": "membership",
        "404_page": "page_not_found",
        "server_error": "server_error"
    }
    
    for test_name in test_matches:
        func_name = re.sub(r'^test_\d*_?', '', test_name)
        broken_functions.append(func_name)
        for prefix, target in route_map.items():
            if prefix in test_name:
                broken_functions.append(target)
    
    # Pattern 3 — AttributeError/NameError format
    attr_pattern = r"has no attribute '(\w+)'"
    attr_matches = re.findall(attr_pattern, error_report)
    broken_functions.extend(attr_matches)
    
    source = read_file(filepath)
    if not source:
        return list(set(broken_functions))
    
    try:
        tree = ast.parse(source)
        real_functions = {
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        verified = [f for f in set(broken_functions) if f in real_functions]
        if verified:
            print(f"🎯 Broken functions identified: {verified}")
        else:
            print("⚠️ No specific functions identified — full review needed")
        return verified
    except SyntaxError:
        return list(set(broken_functions))

def phase_patch_draft_coder(briefing_data: dict, project_paths: dict,
                              error_report: str = "", 
                              max_attempts: int = 3) -> bool:
    """
    TARGETED PATCH PHASE.
    Identifies broken functions from error report.
    Sends ONLY those functions to DRAFT_CODER for fixing.
    Patches them back in place — rest of file untouched.
    """
    from agency.execution import append_delta_log  # Import from execution
    from agency.router import update_change_log    # Avoid circular imports

    production_file = project_paths.get("production", PATHS["production"])
    task = briefing_data.get("task", "Fix reported issues")
    project_name = briefing_data.get("project_name", "unknown")
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n🔧 PATCH ATTEMPT {attempt}/{max_attempts}")
        
        # Step 1 — Identify broken functions
        if error_report:
            broken_funcs = identify_broken_functions(error_report, production_file)
        else:
            broken_funcs = []
        
        if broken_funcs:
            # TARGETED MODE
            print(f"🎯 Targeted patch mode: {broken_funcs}")
            all_patched = True
            
            for func_name in broken_funcs:
                current_func = extract_function_block(production_file, func_name)
                if not current_func:
                    print(f"⚠️ Could not extract {func_name}() — skipping")
                    continue
                
                instruction = f"""You are DRAFT_CODER performing a surgical patch.
You will receive ONE broken function.
Return ONLY the fixed version of that exact function.
Do NOT return the entire file.
Do NOT add imports outside the function.
Do NOT change the function signature unless that is the bug.
Return ONLY valid Python code for that single function."""

                prompt = f"""PROJECT: {project_name}
TASK: {task}

ERROR REPORT:
{prune_error(error_report)}

BROKEN FUNCTION TO FIX:
```python
{current_func}
```

Return ONLY the corrected version of this function.
No explanation. No imports. Just the fixed function code."""

                prompt_with_mem = inject_memory_into_prompt(
                    "DRAFT_CODER", project_paths, prompt
                )
                raw_response = call_agent("DRAFT_CODER", instruction, prompt_with_mem, project_dir=project_paths["root"])
                fixed_func = extract_code_block(raw_response)
                
                if fixed_func:
                    success = apply_function_patch(production_file, func_name, fixed_func)
                    if not success:
                        all_patched = False
                else:
                    print(f"❌ DRAFT_CODER returned no code for {func_name}()")
                    all_patched = False
            
            if all_patched:
                print(f"✅ All targeted patches applied successfully")
                append_delta_log("DRAFT_CODER", "PATCH", attempt, "complete",
                                f"Patched functions: {broken_funcs}", 
                                "Handoff to LOGIC_EXPANDER")
                return True
                
        else:
            # BROAD MODE — user-requested change or unclassified failure
            print("⚠️ Could not identify specific functions — broad patch mode")
            existing_code = read_file(production_file)
            task_desc = briefing_data.get("task") or briefing_data.get("brief") or "Apply requested changes"
            instruction = f"""You are DRAFT_CODER.
Apply ONLY the requested change to the code. Fix errors if an error report is provided.
Return the complete corrected file. Do not refactor unrelated working code."""

            prompt = f"""PROJECT: {project_name}
TASK: {task_desc}

ERROR REPORT:
{prune_error(error_report) if error_report else "none — apply task change only"}

CURRENT CODE:
```python
{existing_code}
```

Return the complete corrected file."""

            prompt_with_mem = inject_memory_into_prompt(
                "DRAFT_CODER", project_paths, prompt
            )
            raw_response = call_agent("DRAFT_CODER", instruction, prompt_with_mem, project_dir=project_paths["root"])
            fixed_code = extract_code_block(raw_response)
            
            if fixed_code:
                write_file(production_file, fixed_code)
                print(f"✅ Broad patch applied")
                return True
    
    print(f"❌ Patch failed after {max_attempts} attempts")
    update_change_log(project_paths, task, "patch", "DRAFT_CODER", 
                     f"FAILED after {max_attempts} attempts")
    return False
