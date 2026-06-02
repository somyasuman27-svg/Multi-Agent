import os
from datetime import datetime
from config import ROOT_DIR
from agency.execution import read_file, append_file

GLOBAL_MEMORY_DIR = os.path.join(ROOT_DIR, "0_Management", "global_agent_memory")

def get_memory_path(agent_role: str, project_paths: dict, scope: str) -> str:
    """Returns path to agent memory file. scope = 'global' or 'local'"""
    # Map active roles to standard files
    role_map = {
        "ceo": "brain",
        "brain": "brain",
        "draft_coder": "draft_coder",
        "logic_expander": "logic_expander",
        "deep_tester": "deep_tester",
        "test_lead": "test_lead",
        "assistant_manager": "assistant_manager",
        "janitor": "ollama",
        "rnd_collector_1": "ollama",
        "rnd_collector_2": "ollama",
    }
    mapped_role = role_map.get(agent_role.lower(), agent_role.lower())
    filename = f"{mapped_role}_memory.md"
    if scope == "global":
        return os.path.join(GLOBAL_MEMORY_DIR, filename)
    else:
        if not project_paths or "root" not in project_paths:
            return ""
        return os.path.join(project_paths["root"], "0_Management", 
                           "local_agent_memory", filename)

def read_agent_memory(agent_role: str, project_paths: dict) -> str:
    """Reads both global and local memory for an agent. Returns combined context."""
    global_path = get_memory_path(agent_role, project_paths, "global")
    local_path = get_memory_path(agent_role, project_paths, "local")
    
    global_mem = read_file(global_path)
    local_mem = read_file(local_path) if local_path else ""
    
    combined = ""
    if global_mem:
        combined += f"=== GLOBAL MEMORY ===\n{global_mem}\n"
    if local_mem:
        combined += f"=== PROJECT MEMORY ===\n{local_mem}\n"
    return combined

def update_agent_memory(agent_role: str, project_paths: dict, 
                        project_name: str, task: str, 
                        result: str, learned: str, avoid: str):
    """Updates both global and local memory after task completion."""
    entry = f"""---
[{datetime.now().strftime('%Y-%m-%d %H:%M')}] [{agent_role}] [{project_name}]
Task: {task[:100]}
Result: {result}
Learned: {learned[:100]}
Avoid: {avoid[:100]}
---
"""
    # Update both scopes
    global_path = get_memory_path(agent_role, project_paths, "global")
    local_path = get_memory_path(agent_role, project_paths, "local")
    if global_path:
        append_file(global_path, entry)
    if local_path:
        append_file(local_path, entry)

def inject_memory_into_prompt(agent_role: str, project_paths: dict, 
                               base_prompt: str) -> str:
    """Injects agent memory at the start of every agent prompt."""
    memory = read_agent_memory(agent_role, project_paths)
    if not memory:
        return base_prompt
    return f"YOUR MEMORY FROM PAST WORK:\n{memory}\n\nCURRENT TASK:\n{base_prompt}"
