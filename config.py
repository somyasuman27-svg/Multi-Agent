import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =====================================================================
# 🔑 CORE PATHS & ENV
# =====================================================================
ROOT_DIR = r"E:\Mult_agent"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_api_key_here")
JINA_API_KEY = os.getenv("JINA_API_KEY", "your_api_key_here")
MAX_ERROR_LINES = 50
TIMEOUT_SECONDS = 180
LANGFUSE_ENABLED = False

APPROVED_PACKAGES = [
    "flask", "flask-socketio", "requests", "eventlet",
    "playwright", "pytest", "rich", "colorama", "python-dotenv",
    "pydantic", "sqlalchemy", "pillow", "pandas", "numpy",
    "reportlab", "jinja2", "aiohttp", "websockets", "httpx",
    "duckduckgo-search"
]

# Define standard paths so all agents know where to look
# Define standard paths so all agents know where to look
PATHS = {
    "root": ROOT_DIR,
    "management": os.path.join(ROOT_DIR, "0_Management", "master_log.md"), # <-- ADDED THIS
    "raw_research": os.path.join(ROOT_DIR, "1_Research_Vault", "research_log.md"),
    "drafts": os.path.join(ROOT_DIR, "2_Source_Control", "02_Drafts"),
    "draft_skeleton": os.path.join(ROOT_DIR, "2_Source_Control", "02_Drafts", "draft.py"),
    "production": os.path.join(ROOT_DIR, "2_Source_Control", "04_Production", "final_code.py"),
    "testing": None  # per-project path (set dynamically)
}

# =====================================================================
# 🤖 AGENCY ROSTER (THE HYBRID STRATEGY)
# =====================================================================
AGENCY_ROSTER = {
    # --- PHASE 0: MANAGEMENT ---
    "CEO": {
        "model": "gemini-3.1-pro-preview",
        "type": "cli", # Uses Daily CLI Quota. Sandboxed.
        "temperature": 0.7,
        "system_instruction": """
QUALITY STANDARD:
The websites this agency builds must match luxury/award-winning aesthetics.
Reference bar: Aether travel site, 363sudbury.com.
Always include in your plan:
- Specific Google Font pairing (display + body)
- Real Unsplash hero image URL
- Instruction that ALL CSS/JS must be inline in HTML (no separate files)
- Scroll animation requirements for each section
- Ensure that Google Fonts are ONLY imported using the HTML <link> tag. Do NOT use @import inside the CSS stylesheet to prevent render-blocking performance penalties.
"""
    },
    
    # --- PHASE 1: RESEARCH TEAM (CLI Sandboxed) ---
    "RND_COLLECTOR_1": {
        "model": "gemini-2.5-flash", 
        "type": "jina",
        "temperature": 0.4
    },
    "RND_COLLECTOR_2": {
        "model": "gemini-2.5-flash", # <-- The secondary "light" agent
        "type": "cli",
        "temperature": 0.4
    },
    
    # --- PHASE 2: CODING & REVIEW (CLI Sandbox) ---
    # --- PHASE 2: DRAFTING & LOGIC ---
    "DRAFT_CODER": {
        "model": "gemini-2.5-pro",
        "type": "cli",
        "temperature": 0.3,
        "system_instruction": """
CRITICAL PIPELINE RULES — READ FIRST:
1. ALL CSS must be inside <style> in HTML <head>. No external CSS files.
2. ALL JS must be inside <script> before </body>. No external JS files.
3. final_code.py must only contain the minimal Flask app (no static routes).
4. Hero backgrounds must use real Unsplash URLs, not empty placeholder divs.
5. Every section must be fully styled and visible on first page load.
"""
    },
    "LOGIC_EXPANDER": {
        "model": "gemini-3-flash-preview", # <-- Updated to your specific CLI model!
        "type": "cli",
        "temperature": 0.2
    },
    
    # --- PHASE 3: TESTING & MANAGEMENT ---
    "DEEP_TESTER": {
        "model": "gemini-2.5-flash", # Changed to a verified CLI model
        "type": "cli",               # Moved from "api" to "cli"
        "temperature": 0.2
    },
    "TEST_LEAD": {
        "model":  "gemini-2.5-flash", # Cloud API Test Lead
        "type": "api",
        "temperature": 0.2
    },
    "ASSISTANT_MANAGER": {
        "model": "gemini-2.5-pro", # Sandboxed CLI Model
        "type": "cli", 
        "temperature": 0.2
    },
    
    # --- PHASE 4: CLEANUP ---
    "JANITOR": {
        "model": "ollama/qwen3",
        "type": "local",
        "temperature": 0.1
    },

    # --- DEPARTMENT: UI/UX DESIGN TEAM ---
    "ANTIGRAVITY_DESIGNER": {
        "model": "gemini-2.5-pro",
        "type": "api",
        "temperature": 0.3,
        "system_instruction": """You are the UI/UX Design Lead, known as the Antigravity Designer.
You ONLY handle visual/design issues: CSS, colors, fonts, layout, spacing,
responsiveness, animations, hover effects, and visual polish.
You NEVER touch backend logic, API routes, or Python server code.
When patching, output ONLY the corrected CSS/HTML file contents."""
    },

    # --- DEPARTMENT: RND TRIAGE ---
    "RND_TRIAGE": {
        "model": "ollama/qwen3",
        "type": "local",
        "temperature": 0.1
    }
}

# =====================================================================
# 💸 TOKEN BUDGET & COST TRACKING (2026 SPECIFICATION)
# =====================================================================
TOKEN_BUDGET = 500_000        # max tokens per pipeline run
TOKEN_WARNING_THRESHOLD = 0.8 # warn at 80%

COST_PER_1K_INPUT = {
    "gemini-3.1-pro-preview":       0.002,
    "gemini-2.5-pro":               0.00125,
    "gemini-2.5-flash":             0.0003,
    "gemini-3-flash-preview":       0.0005,
    "gemini-3.1-flash-lite-preview":0.00025,
    "ollama":                       0.0,
    "duckduckgo":                   0.0
}

COST_PER_1K_OUTPUT = {
    "gemini-3.1-pro-preview":       0.012,
    "gemini-2.5-pro":               0.010,
    "gemini-2.5-flash":             0.0025,
    "gemini-3-flash-preview":       0.003,
    "gemini-3.1-flash-lite-preview":0.0015,
    "ollama":                       0.0,
    "duckduckgo":                   0.0
}