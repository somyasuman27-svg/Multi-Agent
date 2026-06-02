import sys
import os
from config import ROOT_DIR, PATHS
from agency.execution import read_file
from api_bridge import call_agent

if __name__ == "__main__":
    PATHS["root"] = os.path.join(ROOT_DIR, "Active_Projects", "VoltEdge_Electric_Brand_Website")
    PATHS["raw_research"] = os.path.join(PATHS["root"], "1_Research", "research_log.md")
    
    plan = read_file(os.path.join(PATHS["root"], "0_Management", "task_queue.json")) # I don't have the exact CEO plan saved in a file easily accessible, let me just mock it with a large string
    
    instruction = """
    You are the DRAFT_CODER. 
    Your job is to write the initial project code strictly based on the CEO's briefing.
    Output ALL required files using the following strict XML format for each file:
    <file name="path/to/filename.ext">
    ... raw code here ...
    </file>
    For python backend code, use 'final_code.py' as the filename.
    Do not include any conversational text, pleasantries, or explanations.
    """
    
    print("Sending request to DRAFT_CODER...")
    res = call_agent("DRAFT_CODER", instruction, "MOCK PLAN" * 1000, project_dir=PATHS["root"])
    print("Response Length:", len(res))
    print("Response Snippet:", res[:500])
    with open("draft_coder_test_output.txt", "w", encoding="utf-8") as f:
        f.write(res)
