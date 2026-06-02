import os
import re
import json
from datetime import datetime
from config import PATHS, ROOT_DIR
from agency.execution import read_file, write_file, append_file, append_delta_log, update_read_state
from agency.memory import inject_memory_into_prompt

def human_checkpoint(reason, data=None):
    """Pauses execution for critical decisions."""
    print(f"\n🛑 HUMAN CHECKPOINT NEEDED: {reason}")
    if data:
        print(f"📊 DATA PREVIEW:\n{data}")
        
    if os.getenv("AUTO_APPROVE") == "true":
        print("🤖 [AUTO MODE] Automatically approving human checkpoint.")
        return True
    
    while True:
        choice = input("\nDo you approve these changes? (Y/N): ").strip().upper()
        if choice == 'Y':
            print("✅ Approved. Resuming pipeline...")
            return True
        elif choice == 'N':
            print("❌ Denied. Please provide feedback or correct the state manually.")
            return False
        else:
            print("Invalid input. Please enter Y or N.")

def complexity_classifier(task_brief):
    instruction = f"""
    You are the Strict Project Manager (PM) and Lead Technical Architect.
    Your sole task is to analyze incoming project briefs and classify their execution path.
    
    CRITERIA FOR COMPLEX (Full Research Phase Required):
    1. Multi-file execution or multi-language/hybrid code (e.g., Python backend + JavaScript frontend).
    2. Integration of external APIs, cloud resources, web-scraping, web frameworks (Flask, FastAPI, Django).
    3. State management, databases, socket connections, complex algorithms, or gaming loops (Canvas, pygame).
    4. Ambiguous requirements that require technical spec definition and library selection.

    CRITERIA FOR SIMPLE (Direct Drafting Allowed):
    1. Single-file standalone scripts requiring ONLY core Python built-ins or local mathematical/text utility libraries.
    2. Basic automation scripts with no server-side or front-end interface components.

    PROJECT BRIEF TO ANALYZE:
    "{task_brief}"

    OUTPUT FORMAT FORMAT:
    You must output exactly one word, either 'SIMPLE' or 'COMPLEX'. Do not include markdown blocks, punctuation, reasoning, or extra spacing.
    YOUR DECISION:
    """
    
    print("🧠 Classifying task complexity locally via Ollama...")
    from api_bridge import call_agent
    instruction_with_mem = inject_memory_into_prompt("JANITOR", {}, instruction)
    response = call_agent("JANITOR", instruction_with_mem)
    
    raw_response = response.lower()
    if "complex" in raw_response:
        clean_complexity = "complex"
    else:
        clean_complexity = "simple" 
        
    print(f"🤖 Ollama PM Decision: {clean_complexity.upper()}")
    return clean_complexity

# =====================================================================
# 💸 TOKEN TRACKER SYSTEM (PART 2)
# =====================================================================
from config import TOKEN_BUDGET, TOKEN_WARNING_THRESHOLD, COST_PER_1K_INPUT, COST_PER_1K_OUTPUT

class TokenTracker:
    def __init__(self):
        self.session_log = []
        self.total_input = 0
        self.total_output = 0
        self.total_cost = 0.0

    def estimate_tokens(self, text: str) -> int:
        if not text or not isinstance(text, str):
            return 0
        # Rough estimate: 1 token per 4 characters
        return max(1, len(text) // 4)

    def log_call(self, agent_role: str, 
                  model: str,
                  input_text: str, 
                  output_text: str):
        # Sanitize and convert inputs to string defensively
        agent_role = str(agent_role) if agent_role is not None else "unknown"
        model = str(model) if model is not None else "unknown"
        input_text = str(input_text) if input_text is not None else ""
        output_text = str(output_text) if output_text is not None else ""

        input_tokens = self.estimate_tokens(input_text)
        output_tokens = self.estimate_tokens(output_text)

        input_cost = (input_tokens / 1000) * \
            COST_PER_1K_INPUT.get(model, 0)
        output_cost = (output_tokens / 1000) * \
            COST_PER_1K_OUTPUT.get(model, 0)
        call_cost = input_cost + output_cost

        self.total_input += input_tokens
        self.total_output += output_tokens
        self.total_cost += call_cost

        entry = {
            "agent": agent_role,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(call_cost, 6)
        }
        self.session_log.append(entry)
        self._print_call_summary(entry)
        self._check_budget()

    def _print_call_summary(self, entry: dict):
        print(f"  💰 [{entry['agent']}] "
              f"↑{entry['input_tokens']} "
              f"↓{entry['output_tokens']} tokens "
              f"| ${entry['cost_usd']:.4f} "
              f"| Session total: "
              f"${self.total_cost:.4f}")

    def _check_budget(self):
        total_tokens = self.total_input + self.total_output
        usage_pct = total_tokens / TOKEN_BUDGET

        if usage_pct >= 1.0:
            print(f"\n🚨 TOKEN BUDGET EXHAUSTED "
                  f"({total_tokens}/{TOKEN_BUDGET})")
            print("Pipeline halted. Delivering partial report.")
            raise SystemExit("TOKEN_BUDGET_EXCEEDED")

        elif usage_pct >= TOKEN_WARNING_THRESHOLD:
            print(f"\n⚠️  TOKEN WARNING: "
                  f"{int(usage_pct*100)}% of budget used "
                  f"({total_tokens}/{TOKEN_BUDGET} tokens)")

    def print_final_report(self):
        print("\n" + "═" * 50)
        print("   💸 TOKEN SALARY REPORT")
        print("═" * 50)
        for entry in self.session_log:
            bar = "█" * min(20, entry['input_tokens'] // 500)
            print(f"  {entry['agent']:<22} "
                  f"{entry['input_tokens']:>6} in "
                  f"{entry['output_tokens']:>6} out "
                  f"| ${entry['cost_usd']:.4f}")
        print("─" * 50)
        print(f"  {'TOTAL INPUT':<22} {self.total_input:>6} tokens")
        print(f"  {'TOTAL OUTPUT':<22} {self.total_output:>6} tokens")
        print(f"  {'TOTAL COST':<22} ${self.total_cost:.4f} USD")
        budget_used = (
            (self.total_input + self.total_output) 
            / TOKEN_BUDGET * 100
        )
        print(f"  {'BUDGET USED':<22} {budget_used:.1f}%")
        print("═" * 50)

    def get_rate_limit_status(self) -> str:
        total = self.total_input + self.total_output
        pct = total / TOKEN_BUDGET * 100
        if pct < 50:
            return f"🟢 HEALTHY ({pct:.0f}% used)"
        elif pct < 80:
            return f"🟡 MODERATE ({pct:.0f}% used)"
        else:
            return f"🔴 CRITICAL ({pct:.0f}% used)"

# Create global instance
token_tracker = TokenTracker()
