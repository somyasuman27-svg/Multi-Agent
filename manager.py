# manager.py — after split, this is all it contains
import os
from config import ROOT_DIR, PATHS

# Expose package modules for backwards compatibility and easy access
from agency.execution import *
from agency.memory import *
from agency.testing import *
from agency.patching import *
from agency.governance import *
from agency.orchestration import *
from agency.router import *

if __name__ == "__main__":
    BASE_WORKSPACE = os.path.join(ROOT_DIR, "Active_Projects")
    routing = startup_menu(BASE_WORKSPACE)
    
    if routing["mode"] == "new":
        print("\n🏗️ Starting New Project Pipeline...")
        briefing = phase_0_briefing()
        
        if briefing:
            project_name = briefing.get("project", "Auto_Generated_Task")
            dynamic_paths = create_local_project_dir(project_name, BASE_WORKSPACE)
            
            # Update the global PATHS dictionary to use our new isolated folders
            PATHS["root"] = dynamic_paths["root"]
            PATHS["testing"] = dynamic_paths.get("testing") or dynamic_paths.get("3_testing")
            PATHS["production"] = os.path.join(dynamic_paths.get("production") or dynamic_paths.get("04_production"), "final_code.py")
            PATHS["draft_skeleton"] = os.path.join(dynamic_paths.get("drafts") or dynamic_paths.get("2_source_control/drafts"), "draft.py")
            PATHS["raw_research"] = os.path.join(dynamic_paths.get("research") or dynamic_paths.get("1_research"), "research_log.md")
            
            # Run the full pipeline
            run_full_pipeline(briefing, PATHS)
            
    elif routing["mode"] == "existing":
        run_existing_project_pipeline(routing, BASE_WORKSPACE)
    
    elif routing["mode"] == "antigravity":
        antigravity_triage_flow(routing, BASE_WORKSPACE)