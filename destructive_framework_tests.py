import pytest
import os
import sys
import json
import subprocess
import requests
from unittest.mock import patch

# Dynamically add parent directory to python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from agency.governance import TokenTracker
from agency.execution import extract_handoff, get_unread_delta, READ_STATES_FILE
from agency.testing import execute_in_sandbox
from api_bridge import call_agent
from agency.router import call_ollama_direct
from agency.patching import extract_function_block, apply_function_patch

# --- 1. Token Tracker Null Input Crash Test ---
def test_token_tracker_null_input_crash():
    """Verify that TokenTracker.log_call crashes with TypeError when text inputs are None."""
    tracker = TokenTracker()
    with pytest.raises(TypeError):
        tracker.log_call("ceo", "gemini-2.5-flash", None, "valid output")

# --- 2. Greedy Regex Handoff Extraction Failure Test ---
def test_extract_handoff_greedy_regex_bug():
    """Verify that extract_handoff fails when multiple JSON blocks exist due to greedy regex matching."""
    # The regex r'\{.*\}' matches everything between the first { and the last } in the string.
    # Therefore, it matches: {"status": "complete", ...} some text {"status": "retry", ...}
    # This composite string is not valid JSON, causing parse failure.
    raw_output = '{"status": "complete", "handoff_to": "TEST_LEAD", "trial_number": 1, "summary": "test"} middle text {"status": "retry", "handoff_to": "DRAFT_CODER", "trial_number": 1, "summary": "test"}'
    res = extract_handoff(raw_output)
    
    # Due to the greedy regex bug, it fails parsing completely and returns status: "failed"
    assert res["status"] == "failed"
    assert res["error_type"] == "json_parsing"

# --- 3. Read States JSON Corruption Crash Test ---
def test_get_unread_delta_corruption_crash():
    """Verify that get_unread_delta crashes with JSONDecodeError when read states file is corrupted."""
    orig_exists = os.path.exists(READ_STATES_FILE)
    orig_content = ""
    if orig_exists:
        with open(READ_STATES_FILE, 'r', encoding='utf-8') as f:
            orig_content = f.read()
            
    try:
        # Write corrupted JSON
        os.makedirs(os.path.dirname(READ_STATES_FILE), exist_ok=True)
        with open(READ_STATES_FILE, 'w', encoding='utf-8') as f:
            f.write("corrupted {")
            
        with pytest.raises(json.JSONDecodeError):
            get_unread_delta("CEO")
    finally:
        # Restore original state
        if orig_exists:
            with open(READ_STATES_FILE, 'w', encoding='utf-8') as f:
                f.write(orig_content)
        elif os.path.exists(READ_STATES_FILE):
            os.remove(READ_STATES_FILE)

# --- 4. Timeout Message Inconsistency Test ---
def test_execute_in_sandbox_timeout_message_inconsistency():
    """Verify execute_in_sandbox reports a 10s timeout error message even though it runs with a 60s timeout."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["mock"], timeout=60)):
        out, success = execute_in_sandbox("dummy.py")
        assert success is False
        # The returned message claims "10 seconds" even though the process was executed with a 60s timeout
        assert "timed out after 10 seconds" in out

# --- 5. Unsupported Role Agent Dispatch Test ---
def test_api_bridge_unsupported_role():
    """Verify calling an unconfigured agent role returns an error string rather than raising."""
    res = call_agent("INVALID_AGENT_ROLE", "system instruction", "user prompt")
    assert "Error: Role 'INVALID_AGENT_ROLE' not configured." in res

# --- 6. Ollama Down Connection Resiliency Test ---
def test_ollama_direct_server_down():
    """Verify call_ollama_direct falls back to 'UNSURE' gracefully when Ollama is down."""
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError()):
        res = call_ollama_direct("routing decision query")
        assert res == "UNSURE"

# --- 7. Function Extraction Syntax Error Test ---
def test_extract_function_block_syntax_error(tmp_path):
    """Verify extract_function_block returns empty string when parsing a file with syntax errors."""
    bad_file = tmp_path / "syntax_error.py"
    bad_file.write_text("def broken_function():\n    print('missing paren'")
    
    res = extract_function_block(str(bad_file), "broken_function")
    assert res == ""

# --- 8. Patching Missing Function Test ---
def test_apply_function_patch_missing_function(tmp_path):
    """Verify apply_function_patch returns False when function to patch does not exist in target file."""
    test_file = tmp_path / "valid.py"
    test_file.write_text("def existing_function():\n    return 42\n")
    
    res = apply_function_patch(str(test_file), "non_existent_function", "def non_existent_function(): pass")
    assert res is False

if __name__ == '__main__':
    import pytest
    sys.exit(pytest.main([__file__]))
