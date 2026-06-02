import os
os.environ["AUTO_APPROVE"] = "true"
from config import ROOT_DIR, PATHS
from agency.execution import *
from agency.memory import *
from agency.testing import *
from agency.patching import *
from agency.governance import *
from agency.orchestration import *
from agency.router import *

if __name__ == "__main__":
    BASE_WORKSPACE = os.path.join(ROOT_DIR, "Active_Projects")
    print("\n🏗️ Starting New Project Pipeline (Auto Run)...")
    briefing = phase_0_briefing()

    if briefing:
        project_name = briefing.get("project", "Auto_Generated_Task")
        dynamic_paths = create_local_project_dir(project_name, BASE_WORKSPACE)
        
        PATHS["root"] = dynamic_paths["root"]
        PATHS["testing"] = dynamic_paths.get("testing") or dynamic_paths.get("3_testing")
        PATHS["production"] = os.path.join(dynamic_paths.get("production") or dynamic_paths.get("04_production"), "final_code.py")
        PATHS["draft_skeleton"] = os.path.join(dynamic_paths.get("drafts") or dynamic_paths.get("2_source_control/drafts"), "draft.py")
        PATHS["raw_research"] = os.path.join(dynamic_paths.get("research") or dynamic_paths.get("1_research"), "research_log.md")
        
        run_full_pipeline(briefing, PATHS)
