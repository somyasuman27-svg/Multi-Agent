# Graph Report - .  (2026-06-02)

## Corpus Check
- Corpus is ~19,497 words - fits in a single context window. You may not need a graph.

## Summary
- 222 nodes · 599 edges · 15 communities (12 shown, 3 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.83)
- Token cost: 4,926 input · 2,081 output

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

## God Nodes (most connected - your core abstractions)
1. `read_file()` - 33 edges
2. `run_full_pipeline()` - 23 edges
3. `phase_patch_draft_coder()` - 23 edges
4. `write_file()` - 22 edges
5. `call_agent()` - 22 edges
6. `inject_memory_into_prompt()` - 18 edges
7. `phase_2b_logic_expander()` - 18 edges
8. `phase_3_a_test_lead()` - 17 edges
9. `phase_3_b_deep_tester()` - 16 edges
10. `update_read_state()` - 15 edges

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

## Communities (15 total, 3 thin omitted)

### Community 0 - "Pipeline Execution & Orchestration"
Cohesion: 0.10
Nodes (50): append_delta_log(), Updates the byte offset to the current end of the Master Log.     Only call this, Appends a standardized 3-line template to the Master Log., Robust UTF-8 file writer with directory auto-creation and Langfuse tracking., update_read_state(), write_file(), complexity_classifier(), human_checkpoint() (+42 more)

### Community 1 - "Sandbox Testing & Destructive Framework Tests"
Cohesion: 0.06
Nodes (39): extract_handoff(), get_unread_delta(), HandoffSignal, _management_log_path(), str, Extracts the handoff JSON from agent output using regex and Pydantic validation., Seeks to the last read byte offset for the agent and returns only new text., execute_in_sandbox() (+31 more)

### Community 2 - "Router & Framework Infrastructure"
Cohesion: 0.14
Nodes (26): append_file(), log_langfuse_event(), Helper to log miscellaneous events to Langfuse if enabled., Robust UTF-8 file reader with optional Langfuse tracking., Robust UTF-8 file appender with Langfuse tracking., read_file(), call_ollama_direct(), ollama_classify_action() (+18 more)

### Community 3 - "Code block patching & Triage"
Cohesion: 0.15
Nodes (22): extract_all_files(), extract_code_block(), Extracts raw code from markdown blocks., Extracts multiple files from the text using the ==== FILE: ... ==== format., antigravity_triage_flow(), Antigravity Mode: Ollama-powered team triage for existing projects.     Classifi, display_team_logs(), _get_log_path() (+14 more)

### Community 4 - "Function patching & destructive framework tests"
Cohesion: 0.13
Nodes (21): apply_function_patch(), extract_function_block(), identify_broken_functions(), phase_patch_draft_coder(), prune_error(), bool, int, str (+13 more)

### Community 5 - "API Bridge & Search Fallbacks"
Cohesion: 0.16
Nodes (18): _call_cli(), _call_ddg_search(), _call_jina_search(), inject_research_context(), int, str, Automatically attaches the research log to Coders and Testers if it exists., search_with_ddg() (+10 more)

### Community 6 - "Token Tracker & Foundation Tests"
Cohesion: 0.17
Nodes (8): int, str, TokenTracker, Verify that TokenTracker.log_call crashes with TypeError when text inputs are No, test_token_tracker_null_input_crash(), Verify TokenTracker log_call handles completely polluted inputs defensively with, test_token_tracker_extreme_nulls_and_empty_types(), run_foundation_tests()

### Community 7 - "Memory Utilities"
Cohesion: 0.38
Nodes (7): get_memory_path(), str, Reads both global and local memory for an agent. Returns combined context., Updates both global and local memory after task completion., Returns path to agent memory file. scope = 'global' or 'local, read_agent_memory(), update_agent_memory()

## Knowledge Gaps
- **8 isolated node(s):** `int`, `int`, `int`, `str`, `int` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TokenTracker` connect `Token Tracker & Foundation Tests` to `Pipeline Execution & Orchestration`, `Sandbox Testing & Destructive Framework Tests`, `Function patching & destructive framework tests`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Why does `read_file()` connect `Router & Framework Infrastructure` to `Pipeline Execution & Orchestration`, `Sandbox Testing & Destructive Framework Tests`, `Code block patching & Triage`, `Function patching & destructive framework tests`, `Memory Utilities`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `call_agent()` connect `Pipeline Execution & Orchestration` to `Sandbox Testing & Destructive Framework Tests`, `Router & Framework Infrastructure`, `Code block patching & Triage`, `Function patching & destructive framework tests`, `API Bridge & Search Fallbacks`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **What connects `Helper to log miscellaneous events to Langfuse if enabled.`, `Robust UTF-8 file reader with optional Langfuse tracking.`, `Robust UTF-8 file writer with directory auto-creation and Langfuse tracking.` to the rest of the system?**
  _88 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Pipeline Execution & Orchestration` be split into smaller, more focused modules?**
  _Cohesion score 0.10030165912518854 - nodes in this community are weakly interconnected._
- **Should `Sandbox Testing & Destructive Framework Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.05897435897435897 - nodes in this community are weakly interconnected._
- **Should `Router & Framework Infrastructure` be split into smaller, more focused modules?**
  _Cohesion score 0.1380952380952381 - nodes in this community are weakly interconnected._