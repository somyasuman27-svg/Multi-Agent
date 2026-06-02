import pytest
import os
import sys
import json
import subprocess
import requests
import tempfile
from unittest.mock import patch, call

# Dynamically add parent directory to python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from agency.governance import TokenTracker
from agency.execution import extract_handoff, get_unread_delta, READ_STATES_FILE
from agency.testing import execute_in_sandbox, run_tests_safe
from api_bridge import call_agent, _call_jina_search
from agency.router import call_ollama_direct
from agency.triage import ollama_triage_issue, ask_user_triage
from agency.patching import extract_function_block, apply_function_patch, identify_broken_functions

# --- 1. Extreme Nulls and Type Pollution on Token Tracker ---
def test_token_tracker_extreme_nulls_and_empty_types():
    """Verify TokenTracker log_call handles completely polluted inputs defensively without raising TypeErrors."""
    tracker = TokenTracker()
    # Log call with lists, dicts, and None values where strings are expected
    tracker.log_call(
        agent_role=["ceo", "janitor"],
        model={"model": "gemini-2.5-flash"},
        input_text=None,
        output_text=None
    )
    assert tracker.total_input == 0
    assert tracker.total_output == 0
    assert tracker.total_cost == 0.0

# --- 2. Handoff Extraction with Nested Brackets & Malformed Fragments ---
def test_extract_handoff_nested_brackets_and_malformed():
    """Verify extract_handoff handles nested brackets and random braces gracefully without exceptions."""
    raw_output = "Some random text {{{ malformed { JSON data } }}} with incomplete { status: complete }"
    res = extract_handoff(raw_output)
    assert res["status"] == "failed"
    assert res["error_type"] == "json_parsing"

# --- 3. Corrupt Binary States Recovery ---
def test_get_unread_delta_extreme_empty_file():
    """Verify get_unread_delta recovers gracefully when read states file contains garbage binary characters."""
    orig_exists = os.path.exists(READ_STATES_FILE)
    orig_content = ""
    if orig_exists:
        with open(READ_STATES_FILE, 'r', encoding='utf-8') as f:
            orig_content = f.read()
            
    try:
        # Write corrupted binary content
        os.makedirs(os.path.dirname(READ_STATES_FILE), exist_ok=True)
        with open(READ_STATES_FILE, 'wb') as f:
            f.write(b"\x00\xff\x88\x00 corrupted binary content")
            
        # Should not crash, should fallback to empty states dictionary
        delta = get_unread_delta("CEO")
        assert delta is not None
    finally:
        # Restore original state
        if orig_exists:
            with open(READ_STATES_FILE, 'w', encoding='utf-8') as f:
                f.write(orig_content)
        elif os.path.exists(READ_STATES_FILE):
            os.remove(READ_STATES_FILE)

# --- 4. Dynamic Sandbox Timeout Formatting Verification ---
def test_execute_in_sandbox_dynamic_timeout_verification():
    """Verify execute_in_sandbox reports correct timeout duration in its error response dynamically."""
    # subprocess.TimeoutExpired should trigger the exception handler and return e.timeout value dynamically
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["mock"], timeout=15)):
        out, success = execute_in_sandbox("dummy.py")
        assert success is False
        assert "timed out after 15 seconds" in out

# --- 5. Infinite Loop Timeout Sandbox Stress Test ---
def test_execute_in_sandbox_infinite_loop_timeout():
    """Verify execute_in_sandbox aborts an infinite loop in 15 seconds instead of hanging for 60 seconds."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        # Write a script with an infinite loop
        f.write(b"import time\nwhile True:\n    time.sleep(0.1)\n")
        script_path = f.name
        
    try:
        start_time = os.times().elapsed
        import time
        t0 = time.time()
        out, success = execute_in_sandbox(script_path)
        t1 = time.time()
        elapsed = t1 - t0
        
        assert success is False
        assert "timed out after 15 seconds" in out
        # Elapsed time should be around 15 seconds (certainly less than 20 seconds, and nowhere near 60 seconds)
        assert elapsed < 25.0
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)

# --- 6. Ollama Unclosed Thinking Tags Recovery ---
def test_ollama_triage_unclosed_think_tag():
    """Verify triage removes unclosed <think> tags when output is truncated and closing tag is omitted."""
    # If the model gets cut off inside thinking or final response, it might output:
    raw_response = "<think>\nThis is thinking about design issues\nIt might be code or design\n"
    
    # We mock requests.post to return this truncated output
    mock_response = patch("requests.post")
    with mock_response as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"response": raw_response}
        
        # When tag is cleaned, the entire unclosed think block is stripped, returning "unsure" (instead of design_issue)
        res = ollama_triage_issue("button looks ugly", "")
        assert res == "unsure"

# --- 7. Manual Triage Input Loop Resilience ---
def test_ask_user_triage_loop_resilience():
    """Verify ask_user_triage loops on bad/empty inputs and only returns on a valid choice (1/2/3)."""
    # Mock input to yield invalid choices first, then empty string, then finally a valid choice '2'
    with patch("builtins.input", side_effect=["invalid", "", "2"]) as mock_input:
        res = ask_user_triage()
        assert res == "design_issue"
        assert mock_input.call_count == 3

# --- 8. Function Extraction Regex Fallback on Syntax Errors ---
def test_extract_function_block_regex_fallback(tmp_path):
    """Verify extract_function_block falls back to indentation-based regex parsing when file has syntax error."""
    bad_file = tmp_path / "broken_syntax.py"
    bad_file.write_text("""
def working_func():
    return 1

def target_func():
    # AST parse will fail on this line due to unmatched parentheses
    print("missing closing parenthes"
    return 2

def another_func():
    return 3
""")
    
    # The AST parser fails, but the regex fallback successfully extracts the function block by indent!
    res = extract_function_block(str(bad_file), "target_func")
    assert "def target_func():" in res
    assert 'print("missing closing parenthes"' in res
    assert "return 2" in res
    # Should not include working_func or another_func
    assert "working_func" not in res
    assert "another_func" not in res

# --- 9. Test Function Smart Mapping to Production Functions ---
def test_identify_broken_functions_smart_mapping(tmp_path):
    """Verify identify_broken_functions maps test signatures to correct production functions."""
    # Write a mock production file containing standard Flask functions
    prod_file = tmp_path / "final_code.py"
    prod_file.write_text("""
def index():
    return "home"

def menu():
    return "menu"

def reservation():
    return "reserve"
""")
    
    # Simulating a Playwright test log output failure on home_page and menu_page
    error_report = """
    FAILED browser_tests_v1.py::test_home_page_load_and_title - AssertionError: Page URL ...
    FAILED browser_tests_v1.py::test_menu_page_load_and_title - TimeoutError
    """
    
    res = identify_broken_functions(error_report, str(prod_file))
    
    # It should correctly map:
    # test_home_page_load_and_title -> index
    # test_menu_page_load_and_title -> menu
    assert "index" in res
    assert "menu" in res

# --- 10. Jina AI Search Fallback Trigger ---
def test_jina_search_fallback_trigger():
    """Verify Jina Search triggers DDG fallback if no search content is retrieved (only errors/timeouts)."""
    with patch("api_bridge._call_cli", return_value="1. query one\n2. query two\n"), \
         patch("requests.get") as mock_get, \
         patch("api_bridge._call_ddg_search", return_value="DDG_FALLBACK_SUCCESS") as mock_ddg:
        
        # Simulate all Jina HTTP requests returning status code 500 (internal server error)
        mock_get.return_value.status_code = 500
        mock_get.return_value.text = "Internal server error"
        
        res = _call_jina_search("system instruction", "brief description", {"model": "gemini-2.5-flash"})
        
        # Jina returned no successful content blocks, so the system fell back to DDG search
        assert res == "DDG_FALLBACK_SUCCESS"
        mock_ddg.assert_called_once()

if __name__ == '__main__':
    import pytest
    sys.exit(pytest.main([__file__]))
