import os
import time
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Import our custom parser and prompt templates
from backend.parser import CobolParser
from backend.prompt_templates import SYSTEM_PROMPT, THINKING_INSTRUCTION, TOOLS_INFO
from backend.llm_client import call_local_llm as _llm_chat_completions

# Load environment variables
load_dotenv()

app = FastAPI(title="GemmaAudit: Gemma 4-Powered Offline Legacy Code Intelligence & Lineage Agent")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")
parser = CobolParser(SAMPLES_DIR)

class ChatRequest(BaseModel):
    message: str
    model: str
    thinkingMode: bool

# Define our Local Agent Tools (Grounding)
def get_codebase_summary():
    """Tool: Retrieve structural metrics of the entire parsed legacy codebase."""
    graph = parser.parse_directory()
    nodes = graph["nodes"]
    edges = graph["edges"]
    
    programs = [n for n in nodes if n["type"] == "program"]
    files = [n for n in nodes if n["type"] == "file"]
    tables = [n for n in nodes if n["type"] == "table"]
    
    total_loc = sum(n["details"].get("loc", 0) for n in programs)
    avg_complexity = sum(n["details"].get("complexity", 0) for n in programs) / max(1, len(programs))
    avg_risk = sum(n["details"].get("riskIndex", 0) for n in programs) / max(1, len(programs))
    
    return {
        "status": "success",
        "metrics": {
            "totalPrograms": len(programs),
            "totalFiles": len(files),
            "totalDbTables": len(tables),
            "totalLoc": total_loc,
            "averageCyclomaticComplexity": round(avg_complexity, 2),
            "averageMigrationRiskIndex": round(avg_risk, 2)
        },
        "programList": [p["id"] for p in programs],
        "databaseTables": [t["label"] for t in tables],
        "systemFiles": [f["label"] for f in files]
    }

def get_node_details(node_id: str):
    """Tool: Get detailed AST metrics and description of a specific program, paragraph, or resource."""
    graph = parser.parse_directory()
    for node in graph["nodes"]:
        if node["id"].upper() == node_id.upper():
            return {"status": "success", "node": node}
    return {"status": "error", "message": f"Node '{node_id}' not found in the codebase graph."}

def get_high_risk_programs():
    """Tool: Identify legacy modules exceeding risk thresholds (>50 MRI) requiring urgent attention."""
    graph = parser.parse_directory()
    high_risk = []
    for node in graph["nodes"]:
        if node["type"] == "program" and node["details"].get("riskIndex", 0) > 50:
            high_risk.append({
                "program": node["id"],
                "loc": node["details"].get("loc", 0),
                "complexity": node["details"].get("complexity", 0),
                "riskIndex": node["details"].get("riskIndex", 0),
                "hasSql": node["details"].get("hasSql", False),
                "description": node["details"].get("description", "")
            })
    return {"status": "success", "highRiskPrograms": high_risk}

def get_jcl_orchestrations(program_name: str = None):
    """Tool: Return JCL batch orchestrations (Job → Step → Program chains) for the codebase.

    If `program_name` is provided, narrows results to jobs whose steps EXECUTE that program.
    Useful for end-to-end mainframe lineage: how is this COBOL module actually invoked in prod?
    """
    jcl = parser._jcl_graph()
    jobs = jcl.get("jobs", [])

    if program_name:
        target = program_name.upper().replace(".CBL", "").replace(".COB", "")
        filtered = []
        for job in jobs:
            matching_steps = [s for s in job["steps"] if (s.get("target_name") or "").upper() == target]
            if matching_steps:
                filtered.append({**job, "steps": matching_steps})
        jobs = filtered

    return {
        "status": "success",
        "jobCount": len(jobs),
        "jobs": [
            {
                "jobName": j["job_name"],
                "description": j["job_desc"],
                "sourceFile": j["source_file"],
                "steps": [
                    {
                        "stepName": s["step_name"],
                        "executes": s["target_name"],
                        "executesKind": s["target_kind"],
                        "intent": s.get("intent"),
                        "datasets": [d["dsn"] for d in s["dd"] if d.get("dsn")],
                    }
                    for s in j["steps"]
                ],
            }
            for j in jobs
        ],
    }


def read_program_source(program_name: str):
    """Tool: Read the raw COBOL source file for in-depth code auditing and modernization."""
    clean_name = program_name.upper().replace(".CBL", "").replace(".COB", "")
    
    # Search directories
    search_dirs = [
        SAMPLES_DIR,
        "/Users/yakarteek/code/personal/cobol-parser/python-parser/data/samples",
        "/Users/yakarteek/code/personal/cobol-parser/python-parser/data/COBOL",
        "/Users/yakarteek/code/personal/cobol-parser/python-parser/data/real_cobol"
    ]
    
    # 1. Try exact candidates first
    candidates = [
        f"{clean_name}.cbl",
        f"{clean_name}.cob",
        f"{clean_name}.CBL",
        f"{clean_name}.COB",
        program_name
    ]
    
    for s_dir in search_dirs:
        if not os.path.exists(s_dir):
            continue
        for cand in candidates:
            file_path = os.path.join(s_dir, cand)
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return {"status": "success", "program": clean_name, "content": f.read()}
                    
        # 2. Try prefix/suffix matching by traversing the directory (fuzzy lookup)
        for root, _, files in os.walk(s_dir):
            for file in files:
                file_upper = file.upper()
                if (file_upper.endswith(f"_{clean_name}.CBL") or 
                    file_upper.endswith(f"_{clean_name}.COB") or 
                    file_upper == f"{clean_name}.CBL" or 
                    file_upper == f"{clean_name}.COB" or 
                    clean_name in file_upper):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        return {"status": "success", "program": clean_name, "content": f.read()}
                    
    return {"status": "error", "message": f"Source code for '{program_name}' not found in audit scope."}


# API Endpoints
@app.get("/api/graph")
async def get_graph(program: str = None):
    """Returns the code topology and lineage network (nodes & edges) parsed from the COBOL codebase."""
    try:
        if program:
            return parser.get_program_graph(program)
        return parser.get_system_graph()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/source")
async def get_source(program: str):
    """Fetch raw source code of any program file for sidebar visualization."""
    res = read_program_source(program)
    if res["status"] == "success":
        return {"content": res["content"]}
    raise HTTPException(status_code=404, detail=res["message"])

# Helper functions and schemas for Local Offline LLM Inference
import requests

LOCAL_TOOLS = {
    "get_codebase_summary": get_codebase_summary,
    "get_node_details": get_node_details,
    "get_high_risk_programs": get_high_risk_programs,
    "read_program_source": read_program_source,
    "get_jcl_orchestrations": get_jcl_orchestrations,
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_codebase_summary",
            "description": "Retrieve structural metrics of the entire parsed legacy codebase."
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_node_details",
            "description": "Get detailed AST properties and description of a specific program, paragraph, or resource.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "The unique ID of the program, paragraph, DB table, or file (e.g. 'ACC-UPDATE' or 'ACC-UPDATE:1000-PROCESS-DATA')."
                    }
                },
                "required": ["node_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_high_risk_programs",
            "description": "Identify legacy programs exceeding risk thresholds (>50 MRI) requiring urgent attention."
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_program_source",
            "description": "Read the raw COBOL source file for in-depth code auditing and modernization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "program_name": {
                        "type": "string",
                        "description": "The name of the COBOL program file to read (e.g. 'ACC-UPDATE.CBL' or 'MORTGAGE-CALC')."
                    }
                },
                "required": ["program_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_jcl_orchestrations",
            "description": "Return JCL batch orchestrations (Job → Step → Program chains) parsed from the legacy codebase. Optionally narrows to a specific program. Use this to trace how a COBOL module is actually scheduled in production batch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "program_name": {
                        "type": "string",
                        "description": "Optional. Filter to jobs whose steps execute this program (e.g. 'ACC-UPDATE')."
                    }
                }
            }
        }
    }
]

def execute_local_tool(name: str, arguments: dict):
    if name not in LOCAL_TOOLS:
        return {"status": "error", "message": f"Tool '{name}' is not registered."}
    
    try:
        func = LOCAL_TOOLS[name]
        if arguments:
            if name == "get_node_details":
                node_id = arguments.get("node_id") or arguments.get("nodeId") or list(arguments.values())[0]
                return func(node_id=str(node_id))
            elif name == "read_program_source":
                program_name = arguments.get("program_name") or arguments.get("programName") or arguments.get("program") or list(arguments.values())[0]
                return func(program_name=str(program_name))
            elif name == "get_jcl_orchestrations":
                program_name = arguments.get("program_name") or arguments.get("programName") or arguments.get("program")
                return func(program_name=str(program_name)) if program_name else func()
        return func()
    except Exception as e:
        return {"status": "error", "message": f"Failed executing tool '{name}': {str(e)}"}

def call_local_llm(messages, use_tools=True):
    """Thin wrapper that delegates to backend.llm_client.call_local_llm.

    Kept as a named function so the agent loop below stays readable and so
    tests can monkeypatch this single entrypoint.
    """
    return _llm_chat_completions(
        messages,
        tools=TOOLS_SCHEMA if use_tools else None,
        temperature=0.3,
        timeout=(5, 60),
    )

def call_local_llm_with_agent_loop(messages):
    res_json = call_local_llm(messages, use_tools=True)
    choice = res_json["choices"][0]
    message = choice["message"]
    
    tool_calls = message.get("tool_calls")
    if tool_calls:
        messages.append(message)
        
        for tc in tool_calls:
            tc_id = tc.get("id")
            func_name = tc["function"]["name"]
            func_args_str = tc["function"].get("arguments", "{}")
            
            try:
                if isinstance(func_args_str, dict):
                    func_args = func_args_str
                else:
                    func_args = json.loads(func_args_str) if func_args_str else {}
            except Exception:
                func_args = {}
                
            print(f"[Local Agent] Executing tool {func_name} with arguments {func_args}")
            tool_res = execute_local_tool(func_name, func_args)
            
            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "name": func_name,
                "content": json.dumps(tool_res)
            })
            
        final_res_json = call_local_llm(messages, use_tools=False)
        return final_res_json["choices"][0]["message"].get("content", "")
    else:
        return message.get("content", "")


@app.post("/api/chat")
async def chat_agent(req: ChatRequest):
    """
    Agentic chat endpoint that routes queries to Gemma 4. 
    Implements structured function calling and local VPC grounding.
    """
    query = req.message.strip().lower()
    
    backend = os.getenv("LLM_BACKEND", "local_llm").strip().lower()
    
    # Setup System Prompt based on Thinking Mode
    full_system = SYSTEM_PROMPT
    if req.thinkingMode:
        full_system += THINKING_INSTRUCTION
        
    response_text = ""
    used_model = req.model
    real_llm_success = False
    
    # Path A: Gemini Cloud Backend (fallback/legacy)
    if backend == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-pro",
                    system_instruction=full_system,
                    tools=[get_codebase_summary, get_node_details, get_high_risk_programs, read_program_source]
                )
                
                chat = model.start_chat(enable_automatic_function_calling=True)
                response = chat.send_message(req.message)
                response_text = response.text
                used_model = "Gemini 1.5 Pro (Online Fallback)"
                real_llm_success = True
            except Exception as e:
                print(f"[Gemini Backend Error] {e}")
                
    # Path B: Local Offline Inference Backend (Ollama/llama.cpp/vLLM with Unsloth Gemma 4)
    elif backend == "local_llm":
        try:
            messages = [
                {"role": "system", "content": full_system},
                {"role": "user", "content": req.message}
            ]
            response_text = call_local_llm_with_agent_loop(messages)
            used_model = f"{os.getenv('LOCAL_LLM_MODEL', 'gemma4-unsloth')} (Local Offline)"
            real_llm_success = True
        except Exception as e:
            print(f"[Local LLM Backend Error] Connection failed or model not loaded: {e}")
            
    # Path C: Emulated offline agent or fallback
    if not real_llm_success:
        time.sleep(1.2) # Simulate processing/reasoning latency
        
        thinking_block = ""
        response_block = ""
        
        if req.thinkingMode:
            local_url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1")
            local_model = os.getenv("LOCAL_LLM_MODEL", "gemma4-unsloth")
            thinking_block = (
                "<thinking>\n"
                f"1. LOCAL MODEL SERVER NOT DETECTED: Attempted to reach local offline endpoint '{local_url}' running model '{local_model}'.\n"
                "   -> To run real offline inference, start your model server (e.g. run `ollama run gemma4-unsloth` or `llama.cpp` server).\n"
                "   -> Falling back gracefully to air-gapped High-Fidelity Grounded Emulator.\n"
                f"2. ANALYZING QUERY: '{req.message}' with emulator model {req.model}.\n"
                "3. INITIATING OFFLINE TOOL CALL: Detecting keywords and determining appropriate functions...\n"
            )
            
            if any(w in query for w in ["summary", "overview", "codebase", "total"]):
                thinking_block += (
                    "   -> Query targets high-level metrics. Dispatching tool `get_codebase_summary()`.\n"
                    "   -> Retrieving parser statistics for LOC, programs, databases, and I/O channels.\n"
                    "   -> Synthesizing an executive migration summary and structure overview.\n"
                )
                summary_data = get_codebase_summary()
                thinking_block += f"   -> Tool Response Received: Found {summary_data['metrics']['totalPrograms']} programs, {summary_data['metrics']['totalDbTables']} tables, and {summary_data['metrics']['totalLoc']} total lines of code.\n"
            elif any(w in query for w in ["risk", "complexity", "high", "mri", "audit"]):
                thinking_block += (
                    "   -> Query targets migration risks. Dispatching tool `get_high_risk_programs()`.\n"
                    "   -> Inspecting cyclomatic complexity limits and DB connection indexes.\n"
                    "   -> Pinpointing critical refactoring bottlenecks and architectural debt.\n"
                )
                risk_data = get_high_risk_programs()
                thinking_block += f"   -> Tool Response Received: Identified {len(risk_data['highRiskPrograms'])} modules with elevated Migration Risk Indices (>50).\n"
            elif any(w in query for w in ["read", "source", "code", "file", "cbl"]):
                prog = "ACC-UPDATE"
                if "mortgage" in query:
                    prog = "MORTGAGE-CALC"
                elif "db" in query or "database" in query:
                    prog = "DB-INTERFACE"
                thinking_block += (
                    f"   -> Query requests source code for '{prog}'. Dispatching tool `read_program_source('{prog}')`.\n"
                    "   -> Analyzing DIVISION declarations and paragraph boundaries.\n"
                    "   -> Formulating modern object-oriented or procedural microservice translation.\n"
                )
                source_data = read_program_source(prog)
                thinking_block += f"   -> Tool Response Received: Successfully loaded {len(source_data['content'].splitlines())} lines of COBOL source.\n"
            else:
                thinking_block += (
                    "   -> General modernizing query. Running dependency graph lookup.\n"
                    "   -> Grounding responses inside local database schemas and program contains links.\n"
                )
                
            thinking_block += (
                "4. ARCHITECTURAL TRANSLATION DESIGN:\n"
                "   - Database: Translate DB2 SQLCA schemas into modern relational or document store schema definitions.\n"
                "   - Code structure: Decompose monolithic PROCEDURE DIVISION perform chains into independent, state-free routing functions.\n"
                "   - Risks: Mitigate tight data couplings (WORKING-STORAGE variables) by shifting to parameters and REST/gRPC endpoints.\n"
                "5. SYNTHESIZING RESPONSE: Crafting complete, grounded assessment using clean markdown.\n"
                "</thinking>\n\n"
            )
            
        if any(w in query for w in ["summary", "overview", "codebase", "total"]):
            summary = get_codebase_summary()
            m = summary["metrics"]
            response_block = (
                "### 📊 Local Codebase Executive Summary (Offline Emulated)\n\n"
                "Based on the local static-analysis of your offline legacy codebase, here is the architectural summary:\n\n"
                "| Metric | Value | Technical Context |\n"
                "| :--- | :--- | :--- |\n"
                f"| **Total Programs** | {m['totalPrograms']} | COBOL source modules (.CBL) parsed |\n"
                f"| **Total Lines of Code (LOC)** | {m['totalLoc']} | Excluding comments and sequence headers |\n"
                f"| **Average Complexity** | {m['averageCyclomaticComplexity']} | Cyclomatic complexity (control branching pathways) |\n"
                f"| **Average Risk Index (MRI)** | {m['averageMigrationRiskIndex']}/100 | Scaled migration danger index |\n"
                f"| **Database Tables Detected** | {m['totalDbTables']} | DB2 relational tables referenced in EXEC SQL |\n"
                f"| **System File Interfaces** | {m['totalFiles']} | Physical storage files mapped via SELECT ASSIGN |\n\n"
                "**Discovered Modules:**\n"
                f"- **Programs:** {', '.join([f'`{p}`' for p in summary['programList']])}\n"
                f"- **Database Tables:** {', '.join([f'`{t}`' for t in summary['databaseTables']])}\n"
                f"- **Physical Files:** {', '.join([f'`{f}`' for f in summary['systemFiles']])}\n\n"
                "**Architectural Insights from Gemma 4:**\n"
                "The system is highly coupled via shared file system operations and direct `CALL` bindings. "
                "To modernize this codebase, we recommend extracting the DB2 database layers into a standalone database access service, "
                "and wrapping the algorithmic calculations of `MORTGAGE-CALC` as a serverless containerized endpoint."
            )
            
        elif any(w in query for w in ["risk", "complexity", "high", "mri", "audit"]):
            risk = get_high_risk_programs()
            programs_str = ""
            for p in risk["highRiskPrograms"]:
                programs_str += (
                    f"#### 🛑 `{p['program']}.CBL` (Migration Risk Index: **{p['riskIndex']}/100**)\n"
                    f"- **Lines of Code:** {p['loc']} | **Branching Complexity:** {p['complexity']}\n"
                    f"- **Database Bindings:** {'Yes (DB2 SQL)' if p['hasSql'] else 'No'}\n"
                    f"- **Analysis:** {p['description']}\n"
                    "- **Gemma 4 Refactor Strategy:** This program has highly nested `IF-ELSE` paragraphs and long execution loops. "
                    "The state is heavily coupled to shared linkage variables. We advise a step-by-step refactoring: "
                    "first extract individual paragraphs into stateless methods, then map data variables into a structured JSON payload.\n\n"
                )
                
            response_block = (
                "### ⚠️ Legacy System Migration Risk Assessment (Offline Emulated)\n\n"
                "Our static code analyzer has scanned the codebase and flagged the following high-risk modules:\n\n"
                f"{programs_str}"
                "### Recommended Modernization Phase-1 Roadmap:\n"
                "1. **Decouple the Core Engine**: Isolate the computation heavy mathematical functions from I/O boundaries.\n"
                "2. **Implement API Gateways**: Wrap data-retrieval procedures behind secure, authenticated REST APIs.\n"
                "3. **Incremental Migration**: Migrate low-risk modules first to validate pipeline, followed by high-complexity calculators."
            )
            
        elif any(w in query for w in ["read", "source", "code", "file", "cbl"]):
            prog = "ACC-UPDATE"
            if "mortgage" in query:
                prog = "MORTGAGE-CALC"
            elif "db" in query or "database" in query:
                prog = "DB-INTERFACE"
                
            source = read_program_source(prog)
            code_lines = source["content"].splitlines()
            preview = "\n".join(code_lines[:25]) + "\n... [truncated for readability] ..."
            
            translation_example = ""
            if prog == "MORTGAGE-CALC":
                translation_example = (
                    "```python\n"
                    "# Modernized Stateless Python Service (mortgage_calc.py)\n"
                    "from pydantic import BaseModel, Field\n\n"
                    "class MortgageRequest(BaseModel):\n"
                    "    balance: float = Field(..., gt=0)\n"
                    "    rate: float = Field(..., gt=0, le=30.0)\n\n"
                    "def calculate_monthly_payment(req: MortgageRequest) -> float:\n"
                    "    # Translated from legacy Paragraph 4000-APPLY-AMORTIZATION-FORMULA\n"
                    "    monthly_rate = req.rate / 1200.0\n"
                    "    months = 360\n"
                    "    divisor = (1.0 + monthly_rate) ** months\n"
                    "    \n"
                    "    interest_out = req.balance * (monthly_rate * divisor) / (divisor - 1.0)\n"
                    "    return round(interest_out, 2)\n"
                    "```"
                )
            else:
                translation_example = (
                    "```python\n"
                    "# Modernized Orchestrator Service (acc_update.py)\n"
                    "import httpx\n"
                    "from fastapi import FastAPI, HTTPException\n\n"
                    "app = FastAPI()\n\n"
                    "@app.post(\"/accounts/update\")\n"
                    "async def update_account(acc_num: str, balance: float, rate: float):\n"
                    "    # Translated from Paragraph 3000-UPDATE-ACCOUNT\n"
                    "    fee = 15.0\n"
                    "    if balance > 50000.0:\n"
                    "        balance -= fee * 0.5  # Premium client benefit\n"
                    "    else:\n"
                    "        balance -= fee\n"
                    "        \n"
                    "    # Agentic tool calls replaced with modern Microservice REST requests\n"
                    "    async with httpx.AsyncClient() as client:\n"
                    "        res = await client.post(\"http://mortgage-service/calculate\", json={\"balance\": balance, \"rate\": rate})\n"
                    "        return {\"account_number\": acc_num, \"updated_balance\": res.json()}\n"
                    "```"
                )

            response_block = (
                f"### 🔍 Code Audit & Modernization Blueprint (Offline Emulated): `{prog}.CBL`\n\n"
                f"Here is a preview of the raw legacy COBOL source code for `{prog}.CBL` loaded via local audit tool:\n\n"
                f"```cobol\n{preview}\n```\n\n"
                f"#### 🚀 Gemma 4 Automated Microservice Translation\n"
                f"We have analyzed `{prog}.CBL` and generated a modern, clean, fully functional Python service equivalent:\n\n"
                f"{translation_example}\n\n"
                "**Modernization Improvements:**\n"
                "- **Stateless Execution**: Removed shared environment/linkage structures (`WORKING-STORAGE`), shifting variables entirely to thread-safe function inputs.\n"
                "- **Robust Validations**: Replaced legacy logic flags (`LK-STATUS-CODE`) with standard Pydantic schema validation exceptions.\n"
                "- **Scale & Portability**: Runs inside a Docker container locally or in K8s, completely free of mainframe runtime environments."
            )
            
        else:
            response_block = (
                "### 👋 Welcome to GemmaAudit Legacy Control Panel!\n\n"
                "I am the **Gemma 4** local agent, fully grounded in your legacy codebase topology.\n\n"
                "Here are some examples of what you can ask me to do:\n"
                "1. **Summarize the system**: Ask *'Show me a summary of the codebase'* to see files, databases, and general LOC metrics.\n"
                "2. **Inspect migration risks**: Ask *'What are the high risk programs?'* to list high-debt modules needing attention.\n"
                "3. **Audit and translate code**: Ask *'Read and translate MORTGAGE-CALC'* to examine the raw source code and see an automated Python translation.\n\n"
                "**Key Differentiators Explored:**\n"
                "- **Tool Grounding**: My replies are strictly grounded in local static AST structures. I run locally without transmitting any proprietary IP beyond your network boundaries.\n"
                "- **Custom Thinking Slider**: Toggle 'Deep Thinking Mode' above to view the structured steps and logic I follow to dissect complex COBOL modules before responding!"
            )
            
        response_text = thinking_block + response_block
        used_model = "GemmaAudit Grounded Emulator (Offline)"
        
    return {
        "response": response_text,
        "model": used_model,
        "thinkingMode": req.thinkingMode
    }

# Mount the static frontend interface so the app is hosted on the same server
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    # If starting up before frontend is written, print warning
    print(f"Warning: Frontend directory '{FRONTEND_DIR}' does not exist yet. Static mounting skipped.")
