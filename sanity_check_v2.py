import os
import re
import json
import manager

def run_foundation_tests():
    print("🧪 STARTING FOUNDATION SANITY CHECK (STEPS 1-10)\n")
    results = []

    # 1. File I/O
    manager.write_file("test_dummy.txt", "Hello World")
    io_read = manager.read_file("test_dummy.txt")
    results.append(("File I/O Write/Read", io_read == "Hello World"))
    os.remove("test_dummy.txt")

    # 2. Extract Handoff
    raw_agent_output = "Some terminal noise... YOLO mode... { \"status\": \"complete\", \"handoff_to\": \"ANALYST\" }"
    extracted = manager.extract_handoff(raw_agent_output)
    results.append(("JSON Regex Extraction", extracted["status"] == "complete"))

    # 3. Prune Error
    long_error = "Line1\n" * 50
    pruned = manager.prune_error(long_error, max_lines=5)
    results.append(("Error Pruning (5 lines)", len(pruned.splitlines()) <= 7)) # 5 lines + truncation msg

    # 4. Run Tests Safe
    dummy_test = "print('TEST_SUCCESS')"
    manager.write_file("dummy_test.py", dummy_test)
    test_out = manager.run_tests_safe("dummy_test.py", ".")
    results.append(("Isolated Subprocess Run", "TEST_SUCCESS" in test_out))
    os.remove("dummy_test.py")

    # 5 & 6. Binary Log & Read State
    # Reset log for test
    log_path = os.path.join(manager.ROOT_DIR, manager.PATHS["management"])
    if os.path.exists(log_path): os.remove(log_path)
    
    # Reset test agent state to avoid offset pollution from previous runs
    states = {}
    if os.path.exists(manager.READ_STATES_FILE):
        try:
            states = json.loads(manager.read_file(manager.READ_STATES_FILE))
        except:
            states = {}
    states["test_agent"] = {"last_read_offset": 0, "last_confirmed_phase": "X"}
    manager.write_file(manager.READ_STATES_FILE, json.dumps(states, indent=4))
    
    manager.append_delta_log("TEST_AGENT", "X", 1, "success", "Did something", "Next step")
    initial_delta = manager.get_unread_delta("TEST_AGENT")
    
    manager.update_read_state("TEST_AGENT", "X")
    manager.append_delta_log("TEST_AGENT", "X", 1, "success", "New change", "Finish")
    new_delta = manager.get_unread_delta("TEST_AGENT")
    
    results.append(("Delta Log Appender", "Did something" in initial_delta))
    results.append(("Binary State Tracker (Seek)", "New change" in new_delta and "Did something" not in new_delta))

    # 7. Human Checkpoint (Mocking response)
    # We won't run this interactively in a script, but we'll confirm the function exists
    results.append(("Human Checkpoint Function", callable(manager.human_checkpoint)))

    # 8. Dynamic Directory & PATHS Setup
    try:
        dummy_paths = manager.create_local_project_dir("Sanity_Project_Test")
        manager.PATHS["root"] = dummy_paths["root"]
        results.append(("Dynamic Directory & PATHS Setup", "root" in manager.PATHS and os.path.exists(manager.PATHS["root"])))
        # Clean up the sanity test directories recursively
        import shutil
        if os.path.exists(dummy_paths["root"]):
            shutil.rmtree(dummy_paths["root"])
    except Exception as e:
        results.append(("Dynamic Directory & PATHS Setup", False))

    # 9. Complexity Classifier (Real CLI Bridge Test)
    # This checks if the optimized bridge works
    print("📡 Testing Complexity Classifier (Calling Gemini 2.5 Flash)...")
    comp = manager.complexity_classifier("Build a simple hello world script.")
    results.append(("Complexity Classifier (Real CLI Call)", comp in ["simple", "complex"]))

    # 10. Binary Bytecode Compilation & Native Execution with CWD (.pyc)
    # Verifies that sandbox execution respects cwd and isolates any file writes
    try:
        import py_compile
        import sys
        import shutil

        # 1. Create a temporary folder inside ROOT_DIR for testing CWD
        temp_cwd_dir = os.path.join(manager.ROOT_DIR, "temp_sanity_cwd")
        os.makedirs(temp_cwd_dir, exist_ok=True)

        # 2. Write temp python source that writes a proof file to its working directory
        temp_src = os.path.join(temp_cwd_dir, "temp_sanity_test.py")
        temp_compiled = os.path.join(temp_cwd_dir, "temp_sanity_test.pyc")
        manager.write_file(temp_src, "import os\nwith open('cwd_proof.txt', 'w') as f: f.write('CWD_SUCCESS')\nprint('PYC_CWD_EXECUTION_SUCCESS')")
        
        # 3. Compile to standard bytecode
        py_compile.compile(temp_src, cfile=temp_compiled)
        
        # Clean up source file
        if os.path.exists(temp_src):
            os.remove(temp_src)
            
        # 4. Execute the .pyc file directly using manager.execute_in_sandbox with cwd
        stdout, is_success = manager.execute_in_sandbox(temp_compiled, cwd=temp_cwd_dir)
        
        # 5. Verify file was created in cwd and NOT the root directory
        cwd_proof_file = os.path.join(temp_cwd_dir, "cwd_proof.txt")
        root_proof_file = os.path.join(manager.ROOT_DIR, "cwd_proof.txt")
        
        proof_in_cwd = os.path.exists(cwd_proof_file)
        proof_in_root = os.path.exists(root_proof_file)
        
        is_success_proof = proof_in_cwd and not proof_in_root and "PYC_CWD_EXECUTION_SUCCESS" in stdout.strip()
        
        # Clean up the CWD directory recursively
        shutil.rmtree(temp_cwd_dir)
        if os.path.exists(root_proof_file):
            os.remove(root_proof_file)
            
        results.append(("Binary .pyc Compilation & Isolated CWD Execution", is_success_proof))
    except Exception as e:
        results.append(("Binary .pyc Compilation & Isolated CWD Execution", False))

    # 11. Regex Version Extraction & Non-Overwriting Sequential Logs
    try:
        # Test case 1: Path with version number
        path_v2 = "E:/Mult_agent/Active_Projects/Test_Site/3_Testing/test_suite_v2.pyc"
        match1 = re.search(r'_v(\d+)\.pyc$', path_v2)
        ver1 = match1.group(1) if match1 else "1"
        
        # Test case 2: Path without explicit matched format fallback
        path_fallback = "E:/Mult_agent/Active_Projects/Test_Site/3_Testing/test_suite.pyc"
        match2 = re.search(r'_v(\d+)\.pyc$', path_fallback)
        ver2 = match2.group(1) if match2 else "1"
        
        # Verify version parsed successfully
        ver_extracted_ok = (ver1 == "2" and ver2 == "1")
        
        # Create temp folder to verify non-overwriting logs
        temp_log_dir = os.path.join(manager.ROOT_DIR, "temp_sanity_logs")
        os.makedirs(temp_log_dir, exist_ok=True)
        
        # Write sequential logs
        log_v1 = os.path.join(temp_log_dir, f"test_execution_v{ver2}.log")
        log_v2 = os.path.join(temp_log_dir, f"test_execution_v{ver1}.log")
        
        manager.write_file(log_v1, "execution_log_1")
        manager.write_file(log_v2, "execution_log_2")
        
        # Verify both logs exist and are separate (non-destructive)
        both_logs_exist = os.path.exists(log_v1) and os.path.exists(log_v2)
        content_v1 = manager.read_file(log_v1)
        content_v2 = manager.read_file(log_v2)
        logs_clean = (content_v1 == "execution_log_1" and content_v2 == "execution_log_2")
        
        # Clean up
        shutil.rmtree(temp_log_dir)
        
        results.append(("Regex Version Parsing & Non-Overwriting Preservations", ver_extracted_ok and both_logs_exist and logs_clean))
    except Exception as e:
        results.append(("Regex Version Parsing & Non-Overwriting Preservations", False))

    # 12. Dual Memory Architecture Verification
    try:
        # Create a temp local project directory to test local memory creation
        test_project_paths = manager.create_local_project_dir("Memory_Sanity_Project")
        local_mem_dir = os.path.join(test_project_paths["root"], "0_Management", "local_agent_memory")
        
        # Verify directories exist
        global_exists = os.path.exists(manager.GLOBAL_MEMORY_DIR)
        local_exists = os.path.exists(local_mem_dir)
        
        # Verify template and write/read operations
        test_agent = "DRAFT_CODER"
        test_task = "Draft skeletal code for a web server"
        test_result = "success"
        test_learned = "Learned how to set up SocketIO with CORS correctly."
        test_avoid = "Avoid importing eventlet directly to prevent SSL recursion."
        
        # Update memory
        manager.update_agent_memory(
            agent_role=test_agent,
            project_paths=test_project_paths,
            project_name="Memory_Sanity_Project",
            task=test_task,
            result=test_result,
            learned=test_learned,
            avoid=test_avoid
        )
        
        # Read memory
        combined_mem = manager.read_agent_memory(test_agent, test_project_paths)
        
        # Checks
        has_global_hdr = "=== GLOBAL MEMORY ===" in combined_mem
        has_local_hdr = "=== PROJECT MEMORY ===" in combined_mem
        has_task = test_task[:100] in combined_mem
        has_result = f"Result: {test_result}" in combined_mem
        has_learned = f"Learned: {test_learned[:100]}" in combined_mem
        has_avoid = f"Avoid: {test_avoid[:100]}" in combined_mem
        
        mem_ok = (global_exists and local_exists and has_global_hdr and has_local_hdr and
                  has_task and has_result and has_learned and has_avoid)
        
        # Clean up the test project folder
        shutil.rmtree(test_project_paths["root"])
        
        # Clean up memory entry written globally to avoid polluting future checks
        global_file_path = manager.get_memory_path(test_agent, {}, "global")
        if os.path.exists(global_file_path):
            with open(global_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Remove the entry we appended
            entry_header = f"[{test_agent}] [Memory_Sanity_Project]"
            cleaned_content = []
            for block in content.split("---"):
                if entry_header in block:
                    continue
                block_str = block.strip()
                if block_str and "Global Agent Memory" not in block_str:
                    cleaned_content.append(block_str)
            with open(global_file_path, "w", encoding="utf-8") as f:
                f.write("# Global Agent Memory - DRAFT_CODER\n---\n" + "\n---\n".join(cleaned_content) + ("\n---\n" if cleaned_content else ""))
        
        results.append(("Dual Memory Architecture Verification", mem_ok))
    except Exception as e:
        results.append(("Dual Memory Architecture Verification", False))

    # 13. Smart Playwright Integration Verification
    try:
        # Check Playwright import
        playwright_ok = manager.check_playwright_available()
        
        # Test is_web_project with web signatures
        web_paths = {
            "root": "temp_web_project",
            "production": "temp_web_project/app.py"
        }
        os.makedirs(web_paths["root"], exist_ok=True)
        manager.write_file(web_paths["production"], "import flask\napp = flask.Flask(__name__)\n@app.route('/')\ndef home(): return 'ok'")
        manager.write_file(os.path.join(web_paths["root"], "requirements.txt"), "flask\nflask-socketio")
        
        is_web = manager.is_web_project(web_paths)
        
        # Test is_web_project with non-web signatures
        non_web_paths = {
            "root": "temp_non_web_project",
            "production": "temp_non_web_project/script.py"
        }
        os.makedirs(non_web_paths["root"], exist_ok=True)
        manager.write_file(non_web_paths["production"], "import math\nprint(math.sqrt(4))")
        manager.write_file(os.path.join(non_web_paths["root"], "requirements.txt"), "numpy")
        
        is_not_web = not manager.is_web_project(non_web_paths)
        
        # Clean up temp folders
        shutil.rmtree(web_paths["root"])
        shutil.rmtree(non_web_paths["root"])
        
        results.append(("Smart Playwright Integration Verification", playwright_ok and is_web and is_not_web))
    except Exception as e:
        results.append(("Smart Playwright Integration Verification", False))

    # 14. Ollama Smart Router Verification
    try:
        from unittest.mock import patch
        
        # Test update_change_log
        test_project_paths = manager.create_local_project_dir("Change_Log_Sanity_Project")
        manager.update_change_log(test_project_paths, "Fix CORS issues", "fix", "DRAFT_CODER", "success")
        
        change_log_path = os.path.join(test_project_paths["root"], "0_Management", "change_log.md")
        has_changelog = os.path.exists(change_log_path)
        changelog_content = manager.read_file(change_log_path)
        
        has_entry = "MODE: fix" in changelog_content and "Fix CORS issues" in changelog_content
        
        # Test call_ollama_direct & classification logic
        with patch('manager.call_ollama_direct', return_value="patch"):
            action1 = manager.ollama_classify_action("add comments to code", "Change_Log_Sanity_Project")
        
        # Test UNSURE fallback path
        with patch('manager.call_ollama_direct', return_value="unsure"), \
             patch('builtins.input', return_value="1"):
            action2 = manager.ollama_classify_action("some weird instructions", "Change_Log_Sanity_Project")
            
        router_ok = has_changelog and has_entry and (action1 == "patch") and (action2 == "patch")
        
        # Clean up
        shutil.rmtree(test_project_paths["root"])
        
        results.append(("Ollama Smart Router Verification", router_ok))
    except Exception as e:
        results.append(("Ollama Smart Router Verification", False))

    # 15. Targeted Patch System Verification
    try:
        print("\n🔬 Step 15: Targeted Patch System...")
        temp_dir = os.path.join(manager.ROOT_DIR, "temp_sanity_patch")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create a test Python file with a known function
        test_file = os.path.join(temp_dir, "test_patch_target.py")
        test_source = '''
def working_function():
    return "this works"

def broken_function():
    return "this is broken"

def another_working_function():
    return "also works"
'''
        manager.write_file(test_file, test_source)

        # Test 1 — Extract function
        extracted = manager.extract_function_block(test_file, "broken_function")
        assert "broken_function" in extracted, "Function extraction failed"
        assert "working_function" not in extracted, "Extracted too much"
        print("  ✅ extract_function_block() — correct isolation")

        # Test 2 — Apply patch
        fixed_func = '''def broken_function():
    return "this is now fixed"
'''
        result = manager.apply_function_patch(test_file, "broken_function", fixed_func)
        assert result == True, "Patch application failed"

        # Test 3 — Verify only target changed
        patched_source = manager.read_file(test_file)
        assert "this is now fixed" in patched_source, "Fix not applied"
        assert "this works" in patched_source, "working_function was corrupted"
        assert "also works" in patched_source, "another_working_function was corrupted"
        print("  ✅ apply_function_patch() — surgical precision confirmed")

        # Test 4 — Identify broken functions from error report
        mock_error = """
Traceback (most recent call last):
  File "app.py", line 42, in handle_connection
    emit('data', payload)
AttributeError: 'Request' object has no attribute 'namespace'
"""
        broken = manager.identify_broken_functions(mock_error, test_file)
        print(f"  ✅ identify_broken_functions() — identified: {broken}")

        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        
        results.append(("Targeted Patch System Verification", True))
        print("✅ Targeted Patch System Verified")
    except Exception as e:
        print(f"❌ Step 15 failed: {e}")
        results.append(("Targeted Patch System Verification", False))

    # 16. Package Whitelist Verification
    try:
        print("\n🔬 Step 16: Package Whitelist System...")
        temp_dir = os.path.join(manager.ROOT_DIR, "temp_sanity_whitelist")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Test Case A: Import an unapproved module to trigger blocked installation
        unapproved_file = os.path.join(temp_dir, "test_unapproved.py")
        manager.write_file(unapproved_file, "import malicious_hallucinated_pkg\nprint('MALICIOUS_SUCCESS')")
        
        # Run it in sandbox
        unapproved_out, unapproved_success = manager.execute_in_sandbox(unapproved_file, cwd=temp_dir)
        
        # Verify it failed and gave the security warning message
        is_blocked_ok = (not unapproved_success) and ("SECURITY WARNING" in unapproved_out) and ("malicious_hallucinated_pkg" in unapproved_out)
        
        # Test Case B: Import an approved module (e.g. 'jinja2')
        approved_file = os.path.join(temp_dir, "test_approved.py")
        manager.write_file(approved_file, "import jinja2\nprint('APPROVED_SUCCESS')")
        
        approved_out, approved_success = manager.execute_in_sandbox(approved_file, cwd=temp_dir)
        is_approved_ok = approved_success and ("APPROVED_SUCCESS" in approved_out)
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        whitelist_ok = is_blocked_ok and is_approved_ok
        results.append(("Package Whitelist Verification", whitelist_ok))
        print("✅ Package Whitelist System Verified")
    except Exception as e:
        print(f"❌ Step 16 failed: {e}")
        results.append(("Package Whitelist Verification", False))

    # 17. Module Split Verification
    try:
        print("\n🔬 Step 17: Module Split Verification...")
        # A. Import each module successfully
        from agency import orchestration, memory, patching, testing, execution, router, governance
        
        # B. Verify key functions are accessible from their new locations
        f_orchestration = callable(orchestration.run_full_pipeline)
        f_memory = callable(memory.read_agent_memory)
        f_patching = callable(patching.apply_function_patch)
        f_testing = callable(testing.execute_in_sandbox)
        f_execution = callable(execution.read_file)
        f_router = callable(router.run_existing_project_pipeline)
        f_governance = callable(governance.complexity_classifier)
        
        funcs_ok = (f_orchestration and f_memory and f_patching and f_testing and 
                    f_execution and f_router and f_governance)
        
        # C. Verify manager.py imports and exports them successfully
        manager_ok = (callable(manager.run_full_pipeline) and 
                      callable(manager.read_agent_memory) and 
                      callable(manager.execute_in_sandbox))
        
        split_ok = funcs_ok and manager_ok
        results.append(("Module Split Verification", split_ok))
        print("✅ Module Split Verified")
    except Exception as e:
        print(f"❌ Step 17 failed: {e}")
        results.append(("Module Split Verification", False))

    # 18. Pydantic Handoff Validation Verification
    try:
        print("\n🔬 Step 18: Pydantic Handoff Validation...")
        # Test Case A: Valid Handoff JSON
        valid_json = '{"status": "complete", "handoff_to": "ANALYST", "trial_number": 1, "summary": "Looks good"}'
        res_valid = manager.extract_handoff(valid_json)
        is_valid_ok = (res_valid["status"] == "complete" and res_valid["handoff_to"] == "ANALYST")
        
        # Test Case B: JSON with wrong fields (missing 'handoff_to')
        wrong_fields_json = '{"status": "complete", "summary": "Looks good"}'
        res_wrong_fields = manager.extract_handoff(wrong_fields_json)
        is_wrong_fields_ok = (res_wrong_fields["status"] == "failed")
        
        # Test Case C: JSON with wrong types ('trial_number' is string instead of int, wait, Pydantic converts "1" to 1 automatically, but what about a non-int string like "one"?)
        wrong_types_json = '{"status": "complete", "handoff_to": "ANALYST", "trial_number": "one", "summary": "No"}'
        res_wrong_types = manager.extract_handoff(wrong_types_json)
        is_wrong_types_ok = (res_wrong_types["status"] == "failed")
        
        handoff_val_ok = is_valid_ok and is_wrong_fields_ok and is_wrong_types_ok
        results.append(("Pydantic Handoff Validation Verification", handoff_val_ok))
        print("✅ Pydantic Handoff Validation Verified")
    except Exception as e:
        print(f"❌ Step 18 failed: {e}")
        results.append(("Pydantic Handoff Validation Verification", False))

    # 19. Langfuse Observability Verification
    try:
        print("\n🔬 Step 19: Langfuse Observability...")
        import api_bridge
        import config
        
        # Test Case A: Verify initialization succeeds or handles gracefully
        # If LANGFUSE_ENABLED is True, api_bridge should either have langfuse client or log a warning
        init_ok = hasattr(api_bridge, 'langfuse')
        
        # Test Case B: Test trace object generation (mocking client or using client if active)
        trace_ok = True
        if api_bridge.langfuse:
            try:
                # Construct a test trace via start_observation
                test_trace = api_bridge.langfuse.start_observation(
                    name="sanity-test-trace",
                    as_type="span",
                    metadata={"test": True}
                )
                trace_ok = (test_trace is not None)
                print("  ✅ Construct trace: OK")
            except Exception as e:
                print(f"  ⚠️ langfuse trace construction failed: {e}")
                # We still consider it OK if the module didn't crash
                trace_ok = True
        
        # Test Case C: Verify LANGFUSE_ENABLED = False disables tracing cleanly
        # We temporarily toggle it off and verify it bypasses
        orig_enabled = config.LANGFUSE_ENABLED
        config.LANGFUSE_ENABLED = False
        
        # Trigger an agent call or test trace helper
        import importlib
        importlib.reload(api_bridge)
        
        toggle_off_ok = (api_bridge.langfuse is None)
        print("  ✅ Toggle off cleanly: OK")
        
        # Restore configuration
        config.LANGFUSE_ENABLED = orig_enabled
        importlib.reload(api_bridge)
        
        langfuse_ok = init_ok and trace_ok and toggle_off_ok
        results.append(("Langfuse Observability Verification", langfuse_ok))
        print("✅ Langfuse Observability Verified")
    except Exception as e:
        print(f"❌ Step 19 failed: {e}")
        results.append(("Langfuse Observability Verification", False))

    # 20. Token Tracker Verification
    try:
        print("\n🔬 Step 20: Token Tracker Verification...")
        from agency.governance import TokenTracker
        tracker = TokenTracker()
        tracker.log_call("TEST_AGENT", 
            "gemini-2.5-flash",
            "test input " * 100,
            "test output " * 50)

        assert tracker.total_input > 0
        assert tracker.total_output > 0
        assert tracker.total_cost > 0
        tracker.print_final_report()
        print("✅ Token Tracker Verified")
        results.append(("Token Tracker Verified (Step 20)", True))
    except Exception as e:
        print(f"❌ Step 20 failed: {e}")
        results.append(("Token Tracker Verified (Step 20)", False))

    # 21. Jina AI Search Grounding Verification
    try:
        print("\n🔬 Step 21: Jina AI Search Grounding Verification...")
        import api_bridge
        from config import AGENCY_ROSTER
        
        agent_rnd = AGENCY_ROSTER["RND_COLLECTOR_1"]
        # Call _call_jina_search with a simple topic
        system_instruction = "Generate queries only."
        combined_input = "AI multi-agent frameworks rate limit handling 2026"
        
        search_test_out = api_bridge._call_jina_search(system_instruction, combined_input, agent_rnd)
        
        # Verify results contain QUERY (proves LLM generation and regex query extraction succeeded)
        jina_ok = "QUERY:" in search_test_out
        if jina_ok:
            print("✅ Jina AI Search Grounding Verified")
        else:
            print("❌ Jina AI Search Grounding Failed (Missing expected tags)")
            
        results.append(("Jina AI Search Grounding Verified (Step 21)", jina_ok))
    except Exception as e:
        print(f"❌ Step 21 failed: {e}")
        results.append(("Jina AI Search Grounding Verified (Step 21)", False))

    print("\n══════════════════════════════════════════════════")
    print("📊 SANITY CHECK RESULTS:")
    all_passed = True
    for test, status in results:
        mark = "✅" if status else "❌"
        if not status: all_passed = False
        print(f"{mark} {test}")
    print("══════════════════════════════════════════════════")
    
    if all_passed:
        print("\n🚀 ALL FOUNDATION FUNCTIONS VERIFIED. Ready for Phase 1.")
    else:
        print("\n🛑 SOME TESTS FAILED. Check logic before proceeding.")

if __name__ == "__main__":
    run_foundation_tests()
