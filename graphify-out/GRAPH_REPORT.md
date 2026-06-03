# Graph Report - Mult_agent  (2026-06-03)

## Corpus Check
- 23 files · ~16,790 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 242 nodes · 585 edges · 19 communities (14 shown, 5 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.83)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7f02f9d0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Pipeline Execution & Orchestration|Pipeline Execution & Orchestration]]
- [[_COMMUNITY_Sandbox Testing & Destructive Framework Tests|Sandbox Testing & Destructive Framework Tests]]
- [[_COMMUNITY_Router & Framework Infrastructure|Router & Framework Infrastructure]]
- [[_COMMUNITY_Code block patching & Triage|Code block patching & Triage]]
- [[_COMMUNITY_Function patching & destructive framework tests|Function patching & destructive framework tests]]
- [[_COMMUNITY_Token Tracker & Foundation Tests|Token Tracker & Foundation Tests]]
- [[_COMMUNITY_Memory Utilities|Memory Utilities]]
- [[_COMMUNITY_Claude Goal Driven Execution Guide|Claude Goal Driven Execution Guide]]
- [[_COMMUNITY_Claude Simplicity First Principle|Claude Simplicity First Principle]]
- [[_COMMUNITY_Claude Think Before Coding Rule|Claude Think Before Coding Rule]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]

## God Nodes (most connected - your core abstractions)
1. `read_file()` - 35 edges
2. `run_full_pipeline()` - 27 edges
3. `write_file()` - 23 edges
4. `phase_patch_draft_coder()` - 23 edges
5. `call_agent()` - 23 edges
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

## Communities (19 total, 5 thin omitted)

### Community 0 - "Pipeline Execution & Orchestration"
Cohesion: 0.09
Nodes (51): append_delta_log(), extract_handoff(), get_unread_delta(), _management_log_path(), str, Extracts the handoff JSON from agent output using regex and Pydantic validation., Seeks to the last read byte offset for the agent and returns only new text., Updates the byte offset to the current end of the Master Log.     Only call this (+43 more)

### Community 1 - "Sandbox Testing & Destructive Framework Tests"
Cohesion: 0.12
Nodes (17): phase_2_c_post_coding_smoke_gate(), phase_3_b_deep_tester(), Helper to launch a subprocess securely without shell=True., Quick validation after Phase 2 — catches broken imports/paths before test genera, STEP 3B: DEEP_TESTER executes the pre-compiled bytecode test suite (.pyc) direct, STEP 3B: DEEP_TESTER executes the pre-compiled bytecode test suite (.pyc) direct, STEP 3B: DEEP_TESTER executes the pre-compiled bytecode test suite (.pyc) direct, Helper to launch a subprocess securely without shell=True. (+9 more)

### Community 2 - "Router & Framework Infrastructure"
Cohesion: 0.13
Nodes (22): append_file(), HandoffSignal, log_langfuse_event(), Helper to log miscellaneous events to Langfuse if enabled., Robust UTF-8 file appender with Langfuse tracking., get_memory_path(), str, Reads both global and local memory for an agent. Returns combined context. (+14 more)

### Community 3 - "Code block patching & Triage"
Cohesion: 0.08
Nodes (47): Robust UTF-8 file reader with optional Langfuse tracking., read_file(), _auto_fix_coding(), int, apply_function_patch(), extract_function_block(), identify_broken_functions(), phase_patch_draft_coder() (+39 more)

### Community 4 - "Function patching & destructive framework tests"
Cohesion: 0.23
Nodes (13): dequeue_completed_task(), bool, str, Record honest outcomes — no 'success' for coders when tests failed., Executes the full pipeline for a project run., Executes the full pipeline for a project run., Remove the completed task from task_queue.json., Executes the full pipeline for a project run. (+5 more)

### Community 6 - "Token Tracker & Foundation Tests"
Cohesion: 0.31
Nodes (3): int, str, TokenTracker

### Community 7 - "Memory Utilities"
Cohesion: 0.13
Nodes (23): _call_agent_raw(), _call_cli(), _call_ddg_search(), _call_jina_search(), inject_quality_standards(), inject_research_context(), int, str (+15 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (18): Bug 1.1: Token Tracker Crash on Null Inputs (Critical), Bug 1.2: Read States JSON Corruption Crash (High), Bug 1.3: Jina AI Search Fallback Failure (Medium), Bug 1.4: Double Google Font Imports (Low), Bug 2.1: Timeout Error Message Inconsistency (Medium), Bug 2.2: Non-Portable Python Command Invocations (Medium), Bug 2.3: Unbounded Infinite Loop Execution in Sandbox (High), Bug 3.1: Greedy Regex Handoff JSON Parser Bug (High) (+10 more)

### Community 17 - "Community 17"
Cohesion: 0.22
Nodes (8): 1. Requirements, 2. Startup, 3. Running Framework Tests, Antigravity Multi-Agent Agency Framework, 📂 Core Component Registry, 🛠️ Recent Improvements & Resilience Fixes, 🚀 Running the Framework, 🏗️ System Architecture & Workflow

### Community 18 - "Community 18"
Cohesion: 0.33
Nodes (4): 1. Think Before Coding, 2. Simplicity First, 3. Surgical Changes, 4. Goal-Driven Execution

## Knowledge Gaps
- **33 isolated node(s):** `int`, `int`, `int`, `str`, `int` (+28 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `read_file()` connect `Code block patching & Triage` to `Pipeline Execution & Orchestration`, `Sandbox Testing & Destructive Framework Tests`, `Router & Framework Infrastructure`, `Function patching & destructive framework tests`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `TokenTracker` connect `Token Tracker & Foundation Tests` to `Router & Framework Infrastructure`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Why does `call_agent()` connect `Pipeline Execution & Orchestration` to `Sandbox Testing & Destructive Framework Tests`, `Router & Framework Infrastructure`, `Code block patching & Triage`, `Memory Utilities`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **What connects `Helper to log miscellaneous events to Langfuse if enabled.`, `Robust UTF-8 file reader with optional Langfuse tracking.`, `Robust UTF-8 file writer with directory auto-creation and Langfuse tracking.` to the rest of the system?**
  _110 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Pipeline Execution & Orchestration` be split into smaller, more focused modules?**
  _Cohesion score 0.08672699849170437 - nodes in this community are weakly interconnected._
- **Should `Sandbox Testing & Destructive Framework Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._
- **Should `Router & Framework Infrastructure` be split into smaller, more focused modules?**
  _Cohesion score 0.13306451612903225 - nodes in this community are weakly interconnected._