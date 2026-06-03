# Graph Report - Mult_agent  (2026-06-03)

## Corpus Check
- 26 files · ~20,378 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 282 nodes · 677 edges · 23 communities (18 shown, 5 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.83)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9f655804`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Pipeline Execution & Orchestration|Pipeline Execution & Orchestration]]
- [[_COMMUNITY_Sandbox Testing & Destructive Framework Tests|Sandbox Testing & Destructive Framework Tests]]
- [[_COMMUNITY_Router & Framework Infrastructure|Router & Framework Infrastructure]]
- [[_COMMUNITY_Code block patching & Triage|Code block patching & Triage]]
- [[_COMMUNITY_Function patching & destructive framework tests|Function patching & destructive framework tests]]
- [[_COMMUNITY_API Bridge & Search Fallbacks|API Bridge & Search Fallbacks]]
- [[_COMMUNITY_Token Tracker & Foundation Tests|Token Tracker & Foundation Tests]]
- [[_COMMUNITY_Memory Utilities|Memory Utilities]]
- [[_COMMUNITY_Claude Goal Driven Execution Guide|Claude Goal Driven Execution Guide]]
- [[_COMMUNITY_Claude Simplicity First Principle|Claude Simplicity First Principle]]
- [[_COMMUNITY_Claude Think Before Coding Rule|Claude Think Before Coding Rule]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]

## God Nodes (most connected - your core abstractions)
1. `read_file()` - 35 edges
2. `run_full_pipeline()` - 27 edges
3. `call_agent()` - 26 edges
4. `write_file()` - 23 edges
5. `phase_patch_draft_coder()` - 23 edges
6. `phase_2b_logic_expander()` - 21 edges
7. `inject_memory_into_prompt()` - 19 edges
8. `phase_3_a_test_lead()` - 19 edges
9. `phase_3_b_deep_tester()` - 18 edges
10. `update_read_state()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Surgical Changes` --conceptually_related_to--> `agency/patching.py`  [INFERRED]
  CLAUDE.md → agency/patching.py
- `Antigravity Multi-Agent Agency Framework` --references--> `agency/governance.py`  [EXTRACTED]
  README.md → agency/governance.py
- `Antigravity Multi-Agent Agency Framework` --references--> `agency/memory.py`  [EXTRACTED]
  README.md → agency/memory.py
- `Destructive Testing Bug Report` --references--> `agency/governance.py`  [EXTRACTED]
  framework_bug_report.md → agency/governance.py
- `Destructive Testing Bug Report` --references--> `agency/execution.py`  [EXTRACTED]
  framework_bug_report.md → agency/execution.py

## Import Cycles
- None detected.

## Communities (23 total, 5 thin omitted)

### Community 0 - "Pipeline Execution & Orchestration"
Cohesion: 0.10
Nodes (37): _auto_fix_coding(), _coding_agent_instruction(), dequeue_completed_task(), phase_1_a_research_collection(), phase_2_a_draft_coder(), phase_2_b_logic_expander(), phase_2_c_post_coding_smoke_gate(), phase_2_d_quality_review() (+29 more)

### Community 1 - "Sandbox Testing & Destructive Framework Tests"
Cohesion: 0.11
Nodes (20): phase_3_a_test_lead(), phase_3_b_deep_tester(), Helper to launch a subprocess securely without shell=True., STEP 3A: TEST_LEAD executes a smoke test, reviews execution logs,     and compil, STEP 3A: TEST_LEAD executes a smoke test, reviews execution logs,     and compil, STEP 3A: TEST_LEAD executes a smoke test, reviews execution logs,     and compil, STEP 3B: DEEP_TESTER executes the pre-compiled bytecode test suite (.pyc) direct, STEP 3B: DEEP_TESTER executes the pre-compiled bytecode test suite (.pyc) direct (+12 more)

### Community 2 - "Router & Framework Infrastructure"
Cohesion: 0.24
Nodes (11): append_delta_log(), append_file(), extract_handoff(), HandoffSignal, Extracts the handoff JSON from agent output using regex and Pydantic validation., Appends a standardized 3-line template to the Master Log., Robust UTF-8 file appender with Langfuse tracking., ╔══════════════════════════════════════════════════════════════╗ ║          🚀 AN (+3 more)

### Community 3 - "Code block patching & Triage"
Cohesion: 0.10
Nodes (32): antigravity_triage_flow(), Antigravity Mode: Ollama-powered team triage for existing projects.     Classifi, check_playwright_available(), bool, str, Runs test cases in an isolated temp directory.     Strictly follows: shell=False, Checks if Playwright is installed and Chromium is available., run_tests_safe() (+24 more)

### Community 4 - "Function patching & destructive framework tests"
Cohesion: 0.10
Nodes (29): log_langfuse_event(), Helper to log miscellaneous events to Langfuse if enabled., Robust UTF-8 file reader with optional Langfuse tracking., Robust UTF-8 file writer with directory auto-creation and Langfuse tracking., read_file(), write_file(), apply_function_patch(), extract_code_block() (+21 more)

### Community 5 - "API Bridge & Search Fallbacks"
Cohesion: 0.33
Nodes (10): Destructive Testing Bug Report, Surgical Changes, agency/execution.py, agency/governance.py, agency/memory.py, agency/orchestration.py, agency/patching.py, Antigravity Multi-Agent Agency Framework (+2 more)

### Community 6 - "Token Tracker & Foundation Tests"
Cohesion: 0.17
Nodes (8): int, str, TokenTracker, Verify that TokenTracker.log_call crashes with TypeError when text inputs are No, test_token_tracker_null_input_crash(), Verify TokenTracker log_call handles completely polluted inputs defensively with, test_token_tracker_extreme_nulls_and_empty_types(), run_foundation_tests()

### Community 7 - "Memory Utilities"
Cohesion: 0.11
Nodes (24): complexity_classifier(), human_checkpoint(), Pauses execution for critical decisions., phase_0_briefing(), CEO reads the next task from the queue, creates an execution plan,     and assig, call_agent(), _call_agent_raw(), _call_cli() (+16 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (18): Bug 1.1: Token Tracker Crash on Null Inputs (Critical), Bug 1.2: Read States JSON Corruption Crash (High), Bug 1.3: Jina AI Search Fallback Failure (Medium), Bug 1.4: Double Google Font Imports (Low), Bug 2.1: Timeout Error Message Inconsistency (Medium), Bug 2.2: Non-Portable Python Command Invocations (Medium), Bug 2.3: Unbounded Infinite Loop Execution in Sandbox (High), Bug 3.1: Greedy Regex Handoff JSON Parser Bug (High) (+10 more)

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (19): call_ollama_direct(), ollama_classify_action(), int, str, Direct Ollama API call for routing decisions., Runs the correct pipeline for existing project changes.     patch  → DRAFT_CODER, Ollama classifies what action to take on existing project.     Returns: patch /, Appends entry to project change_log.md (+11 more)

### Community 17 - "Community 17"
Cohesion: 0.22
Nodes (8): 1. Requirements, 2. Startup, 3. Running Framework Tests, Antigravity Multi-Agent Agency Framework, 📂 Core Component Registry, 🛠️ Recent Improvements & Resilience Fixes, 🚀 Running the Framework, 🏗️ System Architecture & Workflow

### Community 18 - "Community 18"
Cohesion: 0.33
Nodes (4): 1. Think Before Coding, 2. Simplicity First, 3. Surgical Changes, 4. Goal-Driven Execution

### Community 21 - "Community 21"
Cohesion: 0.16
Nodes (14): get_unread_delta(), _management_log_path(), str, Seeks to the last read byte offset for the agent and returns only new text., Updates the byte offset to the current end of the Master Log.     Only call this, update_read_state(), phase_3_c_assistant_manager(), STEP 3C: ASSISTANT_MANAGER compiles the final delivery report. (+6 more)

### Community 22 - "Community 22"
Cohesion: 0.31
Nodes (9): get_memory_path(), inject_memory_into_prompt(), str, Reads both global and local memory for an agent. Returns combined context., Updates both global and local memory after task completion., Injects agent memory at the start of every agent prompt., Returns path to agent memory file. scope = 'global' or 'local, read_agent_memory() (+1 more)

## Knowledge Gaps
- **33 isolated node(s):** `int`, `int`, `int`, `str`, `int` (+28 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `call_agent()` connect `Memory Utilities` to `Pipeline Execution & Orchestration`, `Sandbox Testing & Destructive Framework Tests`, `Router & Framework Infrastructure`, `Code block patching & Triage`, `Function patching & destructive framework tests`, `Community 21`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `read_file()` connect `Function patching & destructive framework tests` to `Pipeline Execution & Orchestration`, `Sandbox Testing & Destructive Framework Tests`, `Router & Framework Infrastructure`, `Code block patching & Triage`, `Memory Utilities`, `Community 16`, `Community 21`, `Community 22`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `TokenTracker` connect `Token Tracker & Foundation Tests` to `Router & Framework Infrastructure`, `Code block patching & Triage`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **What connects `Helper to log miscellaneous events to Langfuse if enabled.`, `Robust UTF-8 file reader with optional Langfuse tracking.`, `Robust UTF-8 file writer with directory auto-creation and Langfuse tracking.` to the rest of the system?**
  _128 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Pipeline Execution & Orchestration` be split into smaller, more focused modules?**
  _Cohesion score 0.10384068278805121 - nodes in this community are weakly interconnected._
- **Should `Sandbox Testing & Destructive Framework Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.10526315789473684 - nodes in this community are weakly interconnected._
- **Should `Code block patching & Triage` be split into smaller, more focused modules?**
  _Cohesion score 0.10084033613445378 - nodes in this community are weakly interconnected._