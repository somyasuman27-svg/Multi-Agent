import os
import re
import json
from datetime import datetime
from config import ROOT_DIR, PATHS

READ_STATES_FILE = os.path.join(ROOT_DIR, "0_Management", "agent_read_states.json")

def log_langfuse_event(name: str, metadata: dict, level: str = "DEFAULT"):
    """Helper to log miscellaneous events to Langfuse if enabled."""
    from config import LANGFUSE_ENABLED
    if not LANGFUSE_ENABLED:
        return
    try:
        from api_bridge import langfuse
        if langfuse:
            langfuse.create_event(
                name=name,
                metadata=metadata,
                level=level
            )
    except Exception as e:
        print(f"⚠️ Langfuse event log failed: {e}")

def read_file(filepath):
    """Robust UTF-8 file reader with optional Langfuse tracking."""
    import time
    start_time = time.time()
    
    if not os.path.exists(filepath):
        return ""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        elapsed = time.time() - start_time
        log_langfuse_event(
            name="read_file",
            metadata={
                "filepath": filepath,
                "bytes_read": len(content),
                "duration_sec": elapsed
            }
        )
        return content
    except Exception as e:
        print(f"❌ Error reading {filepath}: {str(e)}")
        return ""

def write_file(filepath, content):
    """Robust UTF-8 file writer with directory auto-creation and Langfuse tracking."""
    import time
    start_time = time.time()
    
    try:
        dir_name = os.path.dirname(filepath)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        elapsed = time.time() - start_time
        log_langfuse_event(
            name="write_file",
            metadata={
                "filepath": filepath,
                "bytes_written": len(content),
                "duration_sec": elapsed
            }
        )
        return True
    except Exception as e:
        print(f"❌ Error writing to {filepath}: {str(e)}")
        return False

def append_file(filepath, content):
    """Robust UTF-8 file appender with Langfuse tracking."""
    import time
    start_time = time.time()
    
    try:
        dir_name = os.path.dirname(filepath)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(content)
            
        elapsed = time.time() - start_time
        log_langfuse_event(
            name="append_file",
            metadata={
                "filepath": filepath,
                "bytes_appended": len(content),
                "duration_sec": elapsed
            }
        )
        return True
    except Exception as e:
        print(f"❌ Error appending to {filepath}: {str(e)}")
        return False

from pydantic import BaseModel, ValidationError
from typing import Literal, Optional

class HandoffSignal(BaseModel):
    status: Literal["complete", "failed", "retry"]
    handoff_to: str
    trial_number: int = 1
    error_type: Literal["none", "syntax", "logic", 
                        "architecture", "environment", "test_failure"] = "none"
    summary: str = "none"
    errors: str = "none"
    checkpoint_needed: bool = False

def extract_handoff(raw_output: str) -> dict:
    """
    Extracts the handoff JSON from agent output using regex and Pydantic validation.
    Ensures terminal pollution does not break the pipeline.
    """
    if not isinstance(raw_output, str):
        return {
            "status": "failed",
            "handoff_to": "none",
            "trial_number": 1,
            "error_type": "json_parsing",
            "summary": "Agent failed to provide valid output string.",
            "errors": "Input raw_output is not a string",
            "checkpoint_needed": False
        }
    matches = re.findall(r'\{.*?\}', raw_output, re.DOTALL)
    if matches:
        try:
            parsed_json = json.loads(matches[-1])
            validated = HandoffSignal(**parsed_json)
            return validated.model_dump()
        except (json.JSONDecodeError, ValidationError) as e:
            if isinstance(e, ValidationError):
                print(f"⚠️ Handoff validation failed for JSON: {matches[-1]}")
                print(f"❌ Errors: {e.errors()}")
            
            # Retry once on next-to-last match
            if len(matches) > 1:
                try:
                    parsed_json_retry = json.loads(matches[-2])
                    validated_retry = HandoffSignal(**parsed_json_retry)
                    print("✅ Handoff recovered via next-to-last JSON block!")
                    return validated_retry.model_dump()
                except:
                    pass
            
    return {
        "status": "failed",
        "handoff_to": "none",
        "trial_number": 1,
        "error_type": "json_parsing",
        "summary": "Agent failed to provide valid handoff JSON.",
        "errors": f"Raw output start: {raw_output[:100]}",
        "checkpoint_needed": False
    }

def _management_log_path() -> str:
    path = PATHS["management"]
    return path if os.path.isabs(path) else os.path.join(ROOT_DIR, path)

def get_unread_delta(agent_role: str) -> str:
    """
    Seeks to the last read byte offset for the agent and returns only new text.
    Ensures minimum token burn by avoiding re-reading old history.
    """
    states = {}
    if os.path.exists(READ_STATES_FILE):
        try:
            states = json.loads(read_file(READ_STATES_FILE))
        except Exception as e:
            print(f"⚠️ Warning: Could not parse read states file: {e}")
            states = {}
    
    key = agent_role.lower()
    offset = states.get(key, {}).get("last_read_offset", 0)
    
    log_path = _management_log_path()
    if not os.path.exists(log_path):
        return "No project history found."

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            f.seek(offset)
            return f.read().strip()
    except Exception as e:
        return f"Error reading delta: {str(e)}"

def update_read_state(agent_role: str, phase: str):
    """
    Updates the byte offset to the current end of the Master Log.
    Only call this after a confirmed successful handoff.
    """
    log_path = _management_log_path()
    current_size = os.path.getsize(log_path) if os.path.exists(log_path) else 0
    
    states = {}
    if os.path.exists(READ_STATES_FILE):
        try:
            states = json.loads(read_file(READ_STATES_FILE))
        except:
            states = {}

    key = agent_role.lower()
    states[key] = {
        "last_read_offset": current_size,
        "last_confirmed_phase": phase,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    write_file(READ_STATES_FILE, json.dumps(states, indent=4))

def append_delta_log(agent_name, phase, trial, status, changes, next_steps):
    """
    Appends a standardized 3-line template to the Master Log.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n---\n[{timestamp}] [AGENT: {agent_name}] [PHASE: {phase}] [TRIAL: {trial}] [STATUS: {status}]\n"
    entry += f"Changed: {changes[:200]}\n" # Enforce brevity
    entry += f"Next: {next_steps[:200]}\n---\n"
    
    log_path = _management_log_path()
    return append_file(log_path, entry)
