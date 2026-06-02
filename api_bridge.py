import os
import subprocess
import tempfile
import shutil
import time  # <-- ADDED FOR EXPONENTIAL BACKOFF
import re    # <-- ADDED FOR AUTO-INSTALLER REGEX
import sys   # <-- ADDED FOR CROSS-PLATFORM PATH RESOLUTION
from google import genai
from google.genai import types
from config import AGENCY_ROSTER, GEMINI_API_KEY, PATHS, LANGFUSE_ENABLED, JINA_API_KEY
import requests
from duckduckgo_search import DDGS
from agency.governance import token_tracker

# Initialize Modern GenAI Client
client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize Langfuse client if enabled
langfuse = None
if LANGFUSE_ENABLED:
    try:
        from langfuse import Langfuse
        pub_key = os.getenv("LANGFUSE_PUBLIC_KEY", "pk-lf-dummy")
        sec_key = os.getenv("LANGFUSE_SECRET_KEY", "sk-lf-dummy")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        
        # Initialize client
        langfuse = Langfuse(
            public_key=pub_key,
            secret_key=sec_key,
            host=host
        )
        print("🚀 Langfuse client initialized successfully")
    except Exception as e:
        print(f"⚠️ Failed to initialize Langfuse client: {e}. Disabling tracing.")
        langfuse = None


def search_with_ddg(queries: list, max_results: int = 3) -> str:
    from duckduckgo_search import DDGS
    all_results = []
    with DDGS() as ddgs:
        for query in queries:
            try:
                results = ddgs.text(query, max_results=max_results, backend="html")
                all_results.append(f"QUERY: {query}")
                for r in results:
                    snippet = r.get('body', '')[:500]
                    all_results.append(f"SOURCE: {r.get('href','')}")
                    all_results.append(f"CONTENT: {snippet}")
                all_results.append("---")
            except Exception as e:
                all_results.append(f"QUERY: {query}")
                all_results.append(f"ERROR: {str(e)}")
                all_results.append("---")
    return "\n".join(all_results)

def _call_cli(prompt, agent, project_dir=None):
    model_name = agent["model"]
    gemini_bin = "gemini.cmd" if sys.platform == "win32" else "gemini"
    cmd = [gemini_bin, "-m", model_name, "-y", "--skip-trust", "-p", ""]
    if project_dir and os.path.exists(project_dir):
        process = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            encoding='utf-8', cwd=project_dir, shell=False
        )
        stdout, stderr = process.communicate(input=prompt)
        if stderr and not stdout.strip():
            print(f"⚠️ CLI Error: {stderr.strip()}")
        return stdout.strip()
    else:
        with tempfile.TemporaryDirectory() as temp_sandbox_dir:
            process = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding='utf-8', cwd=temp_sandbox_dir, shell=False
            )
            stdout, stderr = process.communicate(input=prompt)
            return stdout.strip()

def _call_ddg_search(system_instruction, combined_input, agent, role_key=None):
    model_name = agent["model"]
    
    # Step 1: Generate queries via CLI
    query_prompt = f"""
{system_instruction}

TASK: Based on this brief, generate exactly 5 
specific search queries to research this topic.
Output ONLY a numbered list. Nothing else.

BRIEF:
{combined_input[:2000]}
"""
    queries_raw = _call_cli(query_prompt, agent, project_dir=None)
    
    if role_key:
        token_tracker.log_call(
            agent_role=role_key,
            model=agent["model"],
            input_text=query_prompt,
            output_text=queries_raw
        )
    
    # Step 2: Extract queries
    import re
    queries = re.findall(r'\d+\.\s+(.+)', queries_raw)
    if not queries:
        queries = [combined_input[:200]]
    
    # Step 3: DuckDuckGo search
    all_results = []
    with DDGS() as ddgs:
        for query in queries[:5]:
            safe_query = query + " -site:reddit.com"
            results = list(ddgs.text(safe_query, max_results=3))
            all_results.append(f"QUERY: {safe_query}")
            for r in results:
                all_results.append(f"URL: {r.get('href','')}")
                all_results.append(f"CONTENT: {r.get('body','')[:500]}")
            all_results.append("---")
    
    return "\n".join(all_results)

def _call_jina_search(system_instruction, combined_input, agent, role_key=None):
    model_name = agent["model"]
    
    # Step 1: Generate queries via CLI
    query_prompt = f"""
{system_instruction}

TASK: Based on this brief, generate exactly 5 
specific search queries to research this topic.
Output ONLY a numbered list. Nothing else.

BRIEF:
{combined_input[:2000]}
"""
    queries_raw = _call_cli(query_prompt, agent, project_dir=None)
    
    if role_key:
        token_tracker.log_call(
            agent_role=role_key,
            model=agent["model"],
            input_text=query_prompt,
            output_text=queries_raw
        )
    
    # Step 2: Extract queries
    import re
    queries = re.findall(r'\d+\.\s+(.+)', queries_raw)
    if not queries:
        queries = [combined_input[:200]]
    
    # Step 3: Jina AI Search
    all_results = []
    
    # Step 3A: Extract and read reference URLs from the brief
    found_urls = re.findall(r'(https?://[^\s\)\"\',]+)', combined_input)
    unique_urls = []
    for u in found_urls:
        u_clean = u.strip().rstrip(".").rstrip("/")
        if "unsplash.com" in u_clean or "google.com" in u_clean:
            continue
        if u_clean not in unique_urls:
            unique_urls.append(u_clean)
            
    for ref_url in unique_urls[:3]:
        print(f"📖 R&D Team is reading site sample directly via Jina Reader: {ref_url}")
        try:
            jina_reader_url = f"https://r.jina.ai/{ref_url}"
            headers = {
                "Authorization": f"Bearer {JINA_API_KEY}"
            }
            res = requests.get(jina_reader_url, headers=headers, timeout=30)
            if res.status_code == 200:
                all_results.append(f"REFERENCE SITE SAMPLE URL: {ref_url}")
                all_results.append(f"CONTENT:\n{res.text[:3000]}")
                all_results.append("---")
            else:
                res_direct = requests.get(ref_url, timeout=15)
                if res_direct.status_code == 200:
                    all_results.append(f"REFERENCE SITE SAMPLE URL: {ref_url}")
                    all_results.append(f"CONTENT:\n{res_direct.text[:3000]}")
                    all_results.append("---")
        except Exception as e:
            print(f"⚠️ Failed to read site sample {ref_url}: {e}")
            
    for query in queries[:5]:
        try:
            safe_query = query + " -site:reddit.com"
            url = f"https://s.jina.ai/{requests.utils.quote(safe_query)}"
            headers = {
                "Authorization": f"Bearer {JINA_API_KEY}"
            }
            res = requests.get(url, headers=headers, timeout=30)
            if res.status_code == 200:
                all_results.append(f"QUERY: {query}")
                all_results.append(f"CONTENT: {res.text[:1000]}")
            else:
                all_results.append(f"QUERY: {query}")
                all_results.append(f"ERROR: Jina returned status {res.status_code}")
            all_results.append("---")
        except Exception as e:
            all_results.append(f"QUERY: {query}")
            all_results.append(f"ERROR: {str(e)}")
            all_results.append("---")
            
    result_text = "\n".join(all_results)
    # Fallback to DDG search if no queries successfully retrieved content
    if not any("CONTENT:" in block for block in all_results if "QUERY:" in block):
        print("⚠️ Jina search failed entirely (no content retrieved) — falling back to DuckDuckGo...")
        return _call_ddg_search(system_instruction, combined_input, agent, role_key=role_key)
    return result_text

def inject_research_context(role_key, base_prompt):
    """Automatically attaches the research log to Coders and Testers if it exists."""
    # Added TEST_LEAD to this list!
    roles_needing_research = ["DRAFT_CODER", "LOGIC_EXPANDER", "DEEP_TESTER", "TEST_LEAD", "ASSISTANT_MANAGER"]
    
    if role_key in roles_needing_research and os.path.exists(PATHS["raw_research"]):
        with open(PATHS["raw_research"], 'r', encoding='utf-8') as f:
            research_data = f.read()
        return f"{base_prompt}\n\n=== MANDATORY RESEARCH CONTEXT ===\n{research_data}"
    return base_prompt

def call_agent(role_key, system_instruction, user_prompt="", project_dir=None, phase="unknown", trial=1):
    """Langfuse-wrapped agent caller."""
    import time
    
    # Start tracing
    start_time = time.time()
    project_name = os.path.basename(project_dir) if project_dir else "unknown_project"
    
    combined_input = f"SYSTEM INSTRUCTION:\n{system_instruction}\n\nTASK:\n{user_prompt}"
    input_tokens_est = len(combined_input) // 4
    
    agent = AGENCY_ROSTER.get(role_key, {})
    model_name = agent.get("model", "unknown")
    
    trace = None
    generation = None
    if langfuse:
        try:
            trace = langfuse.start_observation(
                name="agent-call",
                as_type="span",
                metadata={
                    "project_name": project_name,
                    "phase": str(phase),
                    "trial": int(trial),
                    "role_key": role_key,
                    "model_name": model_name
                }
            )
            generation = trace.start_observation(
                name=f"agent-{role_key.lower()}",
                as_type="generation",
                model=model_name,
                input=combined_input,
                metadata={"estimated_input_tokens": input_tokens_est}
            )
        except Exception as e:
            print(f"⚠️ Langfuse trace creation failed: {e}")
            
    response_text = _call_agent_raw(role_key, system_instruction, user_prompt, project_dir)
    
    if langfuse and trace and generation:
        try:
            elapsed_time = time.time() - start_time
            output_tokens_est = len(response_text) // 4
            
            if response_text.startswith("🚨"):
                generation.update(
                    output=response_text,
                    status_message=response_text,
                    level="ERROR"
                )
                trace.update(
                    output=response_text,
                    status_message="Failed",
                    level="ERROR"
                )
            else:
                generation.update(
                    output=response_text,
                    status_message="Success",
                    level="DEFAULT"
                )
                trace.update(
                    output=response_text,
                    status_message="Success",
                    level="DEFAULT"
                )
            generation.end()
            trace.end()
        except Exception as e:
            print(f"⚠️ Langfuse update failed: {e}")
            
    return response_text

def _call_agent_raw(role_key, system_instruction, user_prompt="", project_dir=None):
    """Hybrid Router: Routes to Sandboxed CLI or Grounded API based on config. Now with 429 Backoff."""
    
    if role_key not in AGENCY_ROSTER:
        return f"🚨 Error: Role '{role_key}' not configured."
        
    agent = AGENCY_ROSTER[role_key]
    model_name = agent["model"]
    route_type = agent["type"]
    
    # Auto-inject research log for coding/testing roles
    full_prompt = inject_research_context(role_key, user_prompt)
    combined_input = f"SYSTEM INSTRUCTION:\n{system_instruction}\n\nTASK:\n{full_prompt}"

    def _execute_route():
        # =================================================================
        # 🖥️ ROUTE 1: THE STRICT CLI SANDBOX (For Pro & Flash CLI models)
        # =================================================================
        if route_type == "cli":
            # 🎯 PROJECT-SPECIFIC SANDBOX
            if project_dir and os.path.exists(project_dir):
                print(f"🔒 [SANDBOX] Launching {role_key} locked in project directory: {os.path.basename(project_dir)}")
                gemini_bin = "gemini.cmd" if sys.platform == "win32" else "gemini"
                cmd = [gemini_bin, "-m", model_name, "-y", "--skip-trust", "-p", ""]
                
                # Note: We use the real project_dir as the Current Working Directory (cwd)
                process = subprocess.Popen(
                    cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    encoding='utf-8', cwd=project_dir, shell=False
                )
                stdout, stderr = process.communicate(input=combined_input)
                if stderr and not stdout.strip():
                    print(f"⚠️ CLI Error (project): {stderr.strip()}")
                
                result = stdout.strip()
                if not result:
                    print("⚠️ CLI returned empty. Falling back to native Python SDK!")
                    try:
                        print(f"⚠️ Switching to fallback model: gemini-2.5-flash for {role_key} (CLI SDK fallback)...")
                        response = client.models.generate_content(model="gemini-2.5-flash", contents=combined_input)
                        return response.text
                    except Exception as e:
                        print(f"🚨 SDK Fallback to gemini-2.5-flash failed: {e}")
                        return ""
                return result

            # 🛸 GENERIC TEMP SANDBOX (Fallback)
            else:
                print(f"🔒 [SANDBOX] Launching {role_key} in isolated temp directory...")
                with tempfile.TemporaryDirectory() as temp_sandbox_dir:
                    gemini_bin = "gemini.cmd" if sys.platform == "win32" else "gemini"
                    cmd = [gemini_bin, "-m", model_name, "-y", "--skip-trust", "-p", ""]
                    process = subprocess.Popen(
                        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        encoding='utf-8', cwd=temp_sandbox_dir, shell=False
                    )
                    stdout, stderr = process.communicate(input=combined_input)
                    if stderr and not stdout.strip():
                        print(f"⚠️ CLI Error (temp): {stderr.strip()}")
                        
                    result = stdout.strip()
                    if not result:
                        print("⚠️ CLI returned empty. Falling back to native Python SDK!")
                        try:
                            print(f"⚠️ Switching to fallback model: gemini-2.5-flash for {role_key} (CLI SDK fallback)...")
                            response = client.models.generate_content(model="gemini-2.5-flash", contents=combined_input)
                            return response.text
                        except Exception as e:
                            print(f"🚨 SDK Fallback to gemini-2.5-flash failed: {e}")
                            return ""
                    return result
        # =================================================================
        elif route_type == "ddg":
            return _call_ddg_search(system_instruction, combined_input, agent, role_key)
        elif route_type == "jina":
            return _call_jina_search(system_instruction, combined_input, agent, role_key)

        # =================================================================
        # =================================================================
        elif route_type == "api_search":
            print(f"🌐 [API-SEARCH] Launching {role_key} ({model_name}) with Google Grounding...")
            search_config = types.GenerateContentConfig(
                system_instruction=system_instruction, temperature=agent["temperature"],
                tools=[{"googleSearch": {}}] 
            )
            
            # Build candidate fallback chain
            fallback_chain = []
            if "fallback" in agent:
                fallback_chain.append(agent["fallback"])
            for d in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite"]:
                if d != model_name and d not in fallback_chain:
                    fallback_chain.append(d)
                    
            candidate_models = [model_name] + fallback_chain
            
            last_error = None
            for current_model in candidate_models:
                if current_model != model_name:
                    print(f"⚠️ Switching to fallback model: {current_model} for {role_key} (api_search)...")
                    
                max_retries = 3 if current_model == model_name else 1
                base_wait = 2
                
                for attempt in range(max_retries):
                    try:
                        response = client.models.generate_content(
                            model=current_model, contents=full_prompt, config=search_config
                        )
                        return response.text
                    except Exception as e:
                        err_msg = str(e)
                        last_error = err_msg
                        is_429 = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg
                        is_transient = any(code in err_msg for code in ["429", "503", "500", "504"])
                        
                        if is_transient:
                            if is_429:
                                if attempt < 1:  # Only retry once for 429
                                    wait_time = base_wait
                                    print(f"🚨 429 Quota Exceeded! Retrying once in {wait_time}s...")
                                    time.sleep(wait_time)
                                    continue
                                else:
                                    print(f"🚨 429 Quota persists for {current_model}. Moving to next fallback in chain.")
                                    break
                            else:
                                if attempt < max_retries - 1:
                                    wait_time = base_wait * (2 ** attempt)
                                    print(f"🚨 Transient API error ({err_msg})! Retrying in {wait_time}s...")
                                    time.sleep(wait_time)
                                    continue
                                else:
                                    break
                        else:
                            print(f"🚨 Non-transient API error ({err_msg}) for {current_model}.")
                            break
                            
            return f"🚨 API Search failed after trying all candidate models. Last error: {last_error}"

        # =================================================================
        # ☁️ ROUTE 3: STANDARD API (For 1.5 Testers) + BACKOFF
        # =================================================================
        elif route_type == "api":
            print(f"☁️ [API] Launching {role_key} ({model_name}) in the cloud...")
            
            # Build candidate fallback chain
            fallback_chain = []
            if "fallback" in agent:
                fallback_chain.append(agent["fallback"])
            for d in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite"]:
                if d != model_name and d not in fallback_chain:
                    fallback_chain.append(d)
                    
            candidate_models = [model_name] + fallback_chain
            
            last_error = None
            for current_model in candidate_models:
                if current_model != model_name:
                    print(f"⚠️ Switching to fallback model: {current_model} for {role_key} (api)...")
                    
                max_retries = 3 if current_model == model_name else 1
                base_wait = 2
                
                for attempt in range(max_retries):
                    try:
                        response = client.models.generate_content(
                            model=current_model, contents=full_prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction, temperature=agent["temperature"]
                            )
                        )
                        return response.text
                    except Exception as e:
                        err_msg = str(e)
                        last_error = err_msg
                        is_429 = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg
                        is_transient = any(code in err_msg for code in ["429", "503", "500", "504"])
                        
                        if is_transient:
                            if is_429:
                                if attempt < 1:  # Only retry once for 429
                                    wait_time = base_wait
                                    print(f"🚨 429 Quota Exceeded! Retrying once in {wait_time}s...")
                                    time.sleep(wait_time)
                                    continue
                                else:
                                    print(f"🚨 429 Quota persists for {current_model}. Moving to next fallback in chain.")
                                    break
                            else:
                                if attempt < max_retries - 1:
                                    wait_time = base_wait * (2 ** attempt)
                                    print(f"🚨 Transient API error ({err_msg})! Retrying in {wait_time}s...")
                                    time.sleep(wait_time)
                                    continue
                                else:
                                    break
                        else:
                            print(f"🚨 Non-transient API error ({err_msg}) for {current_model}.")
                            break
                            
            return f"🚨 API Standard failed after trying all candidate models. Last error: {last_error}"

        # =================================================================
        # 🏠 ROUTE 4: LOCAL OLLAMA (For zero-cost tasks)
        # =================================================================
        elif route_type == "local":
            print(f"🏠 [LOCAL] Launching {role_key} ({model_name}) via Ollama...")
            actual_model = model_name.replace("ollama/", "") 
            try:
                res = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": actual_model, "prompt": combined_input, "stream": False, "options": {"temperature": agent["temperature"]}},
                    timeout=120
                )
                if res.status_code == 200:
                    return res.json().get("response", "").strip()
                else:
                    return f"🚨 Ollama HTTP Error: {res.text}"
            except requests.exceptions.ConnectionError:
                return "🚨 Ollama Connection Error: Is the Ollama app running on your PC?"
            except Exception as e:
                return f"🚨 Ollama Crash: {str(e)}"
                
        return "🚨 Route type not recognized."

    raw_output = _execute_route()

    if route_type not in ["ddg", "jina"]:
        token_tracker.log_call(
            agent_role=role_key,
            model=agent["model"],
            input_text=combined_input,
            output_text=raw_output
        )

    return raw_output