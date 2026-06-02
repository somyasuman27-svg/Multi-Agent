"""
╔══════════════════════════════════════════════════════════════╗
║          🚀 ANTIGRAVITY CLI — Team-Routed Triage            ║
║                                                              ║
║  Ollama-powered issue classification for multi-team agency   ║
║  🔧 RnD (Code Team)  ←→  🎨 UI/UX (Design Team)            ║
╚══════════════════════════════════════════════════════════════╝

Usage:
    python antigravity.py           — Interactive mode
    python antigravity.py --auto    — Auto-approve mode (skip human checkpoints)
"""
import os
import sys

# Handle --auto flag
if "--auto" in sys.argv:
    os.environ["AUTO_APPROVE"] = "true"

from config import ROOT_DIR, PATHS
from agency.execution import *
from agency.memory import *
from agency.testing import *
from agency.patching import *
from agency.governance import *
from agency.orchestration import *
from agency.router import startup_menu, run_existing_project_pipeline, antigravity_triage_flow


def print_banner():
    """Print the Antigravity CLI startup banner."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          🚀  A N T I G R A V I T Y   C L I                  ║
║          ─────────────────────────────────                   ║
║          Team-Routed Development Agency                      ║
║                                                              ║
║   🔧 RnD Team    → Code / Logic / Backend / Tests           ║
║   🎨 UI/UX Team  → CSS / Layout / Fonts / Animations        ║
║                                                              ║
║   Powered by Ollama (qwen3) + Gemini Agents                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)


def main():
    print_banner()

    BASE_WORKSPACE = os.path.join(ROOT_DIR, "Active_Projects")

    # Use the enhanced startup menu (now includes Antigravity Mode)
    routing = startup_menu(BASE_WORKSPACE)

    if routing["mode"] == "new":
        # ─── NEW PROJECT PIPELINE ──────────────────────────────────────
        print("\n🏗️ Starting New Project Pipeline...")
        briefing = phase_0_briefing()

        if briefing:
            project_name = briefing.get("project", "Auto_Generated_Task")
            dynamic_paths = create_local_project_dir(project_name, BASE_WORKSPACE)

            # Update the global PATHS dictionary
            PATHS["root"] = dynamic_paths["root"]
            PATHS["testing"] = dynamic_paths.get("testing") or dynamic_paths.get("3_testing")
            PATHS["production"] = os.path.join(
                dynamic_paths.get("production") or dynamic_paths.get("04_production"),
                "final_code.py"
            )
            PATHS["draft_skeleton"] = os.path.join(
                dynamic_paths.get("drafts") or dynamic_paths.get("2_source_control/drafts"),
                "draft.py"
            )
            PATHS["raw_research"] = os.path.join(
                dynamic_paths.get("research") or dynamic_paths.get("1_research"),
                "research_log.md"
            )

            run_full_pipeline(briefing, PATHS)

    elif routing["mode"] == "existing":
        # ─── CLASSIC EXISTING PROJECT PIPELINE ─────────────────────────
        run_existing_project_pipeline(routing, BASE_WORKSPACE)

    elif routing["mode"] == "antigravity":
        # ─── 🚀 ANTIGRAVITY MODE (TEAM TRIAGE) ────────────────────────
        antigravity_triage_flow(routing, BASE_WORKSPACE)

    else:
        print("❌ Unknown routing mode. Exiting.")


if __name__ == "__main__":
    main()
