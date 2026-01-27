#!/usr/bin/env python3
"""
🐕 BARK DISSECTOR - Ralph Wiggum Mode v2
"I'm learnding!"

Autonomous agent that relentlessly analyzes suno-ai/bark until fully understood.
No chat. No stopping. Just keeps going until done.

FALLBACK CHAIN:
1. xai-sdk (preferred - has tools)
2. Direct HTTP to Grok API

Features:
- C4 architecture diagrams
- Success criteria per phase
- Self-healing (removes broken backends)
"""

import os
import sys
import json
import subprocess
import time
import re
import httpx
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
from dataclasses import dataclass, field

# === CONFIG ===

def _load_env_file(path: Path):
    if not path.exists():
        return
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _load_from_zshrc(path: Path):
    if not path.exists():
        return
    pattern = re.compile(r'^\s*export\s+([A-Za-z_][A-Za-z0-9_]*)=(.*)$')
    for line in path.read_text(errors="ignore").splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        key, value = match.group(1), match.group(2)
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(Path(__file__).parent / ".env")
_load_from_zshrc(Path.home() / ".zshrc")

XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
XAI_MCP_SERVER_URL = os.environ.get("XAI_MCP_SERVER_URL", "")
ALLOW_WEB_TOOLS = os.environ.get("ALLOW_WEB_TOOLS", "false").lower() in {"1", "true", "yes"}
DEEPTHINKING_MCP_COMMAND = os.environ.get("DEEPTHINKING_MCP_COMMAND", "node")
DEEPTHINKING_MCP_ARGS = os.environ.get(
    "DEEPTHINKING_MCP_ARGS",
    "/Users/cameronbrooks/deepthinking-mcp/dist/index.js"
).split()
DEEPTHINKING_MCP_CWD = os.environ.get("DEEPTHINKING_MCP_CWD", "/Users/cameronbrooks/deepthinking-mcp")

BARK_REPO_URL = os.environ.get("BARK_REPO_URL", "https://github.com/suno-ai/bark")
BARK_REPO_PATH = Path(os.environ.get("BARK_REPO_PATH", "/Users/cameronbrooks/bark"))
WORK_DIR = Path(__file__).parent / "bark_analysis"
OUTPUT_FILE = Path(os.environ.get("OUTPUT_FILE", str(WORK_DIR / "BARK_DISSECTION.md")))
STATE_FILE = WORK_DIR / ".dissector_state.json"

MODELS = {
    "xai_sdk": "grok-4-1-fast-reasoning",
    "xai_http": "grok-4-1-fast-reasoning",
}


# === BACKEND ABSTRACTION ===

@dataclass
class Backend:
    name: str
    call: Callable
    available: bool = True
    errors: int = 0
    max_errors: int = 3


class LLMRouter:
    """Tries backends in order, removes ones that fail repeatedly."""
    
    def __init__(self):
        self.backends: list[Backend] = []
        self._init_backends()
    
    def _init_backends(self):
        """Initialize available backends."""
        
        # 1. xai-sdk (best - has tools)
        if XAI_API_KEY:
            try:
                from xai_sdk import Client
                self.backends.append(Backend(
                    name="xai_sdk",
                    call=self._call_xai_sdk
                ))
                print("✅ xai-sdk available")
            except ImportError:
                print("⚠️ xai-sdk not installed")
        
        # 2. Direct HTTP to Grok
        if XAI_API_KEY:
            self.backends.append(Backend(
                name="xai_http",
                call=self._call_xai_http
            ))
            print("✅ xai-http fallback ready")
        
        if not self.backends:
            print("❌ No LLM backends available!")
            print("   Set XAI_API_KEY")
            sys.exit(1)
    
    def _call_xai_sdk(self, prompt: str, system: str = "") -> str:
        """Call via xai-sdk with server-side tools enabled."""
        from xai_sdk import Client
        from xai_sdk.chat import user, tool, tool_result
        from xai_sdk.tools import code_execution, get_tool_call_type, mcp
        from xai_sdk.search import SearchParameters
        
        client = Client(api_key=XAI_API_KEY, timeout=3600)
        tools = [code_execution()]
        if ALLOW_WEB_TOOLS:
            from xai_sdk.tools import web_search, x_search
            tools.extend([web_search(), x_search()])
        if XAI_MCP_SERVER_URL:
            tools.append(mcp(server_url=XAI_MCP_SERVER_URL))

        def read_local_file(path: str) -> str:
            target = Path(path).expanduser().resolve()
            repo_root = BARK_REPO_PATH.resolve()
            if not str(target).startswith(str(repo_root)):
                return f"[DENIED] {target} is outside {repo_root}"
            return read_file_safe(target, max_chars=20000)

        tools.append(
            tool(
                name="read_local_file",
                description="Read a text file under the local Bark repo by path.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute or repo-relative file path",
                        }
                    },
                    "required": ["path"],
                },
            )
        )
        tools.append(
            tool(
                name="deepthinking_mcp",
                description="Call the local DeepThinking MCP server over stdio.",
                parameters={
                    "type": "object",
                    "properties": {
                        "tool": {
                            "type": "string",
                            "description": "DeepThinking tool name (use __list__ to list tools)",
                        },
                        "arguments": {
                            "type": "object",
                            "description": "Tool arguments JSON object",
                        },
                    },
                    "required": ["tool"],
                },
            )
        )

        chat = client.chat.create(
            model=MODELS["xai_sdk"],
            tools=tools,
            search_parameters=SearchParameters(mode="auto"),
        )
        
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        chat.append(user(full_prompt))
        
        response_text = ""
        response = None
        client_side_tool_calls = []
        for response, chunk in chat.stream():
            for tool_call in chunk.tool_calls:
                tool_type = get_tool_call_type(tool_call)
                if tool_type == "client_side_tool":
                    client_side_tool_calls.append(tool_call)
                else:
                    print(f"   🧰 Tool call: {tool_call.function.name} {tool_call.function.arguments}")
            if chunk.content:
                response_text += chunk.content

        if client_side_tool_calls:
            for tool_call in client_side_tool_calls:
                args = json.loads(tool_call.function.arguments or "{}")
                if tool_call.function.name == "read_local_file":
                    result_text = read_local_file(args.get("path", ""))
                elif tool_call.function.name == "deepthinking_mcp":
                    result_text = call_deepthinking_mcp(
                        args.get("tool", ""),
                        args.get("arguments", {}) or {}
                    )
                else:
                    result_text = f"[ERROR] Unknown client-side tool: {tool_call.function.name}"
                chat.append(tool_result(result_text))
            for response, chunk in chat.stream():
                if chunk.content:
                    response_text += chunk.content

        if response and getattr(response, "server_side_tool_usage", None):
            print(f"   🧰 Tool usage: {response.server_side_tool_usage}")
        
        return response_text
    
    def _call_xai_http(self, prompt: str, system: str = "") -> str:
        """Direct HTTP to Grok API."""
        url = "https://api.x.ai/v1/chat/completions"
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODELS["xai_http"],
                "messages": messages,
                "max_tokens": 8192,
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    
    def call(self, prompt: str, system: str = "") -> tuple[str, str]:
        """
        Call LLM with fallback chain.
        Returns (response, backend_used)
        """
        available = [b for b in self.backends if b.available]
        
        if not available:
            raise RuntimeError("All backends failed and were removed!")
        
        for backend in available:
            try:
                print(f"   🔌 Trying {backend.name}...", end=" ", flush=True)
                response = backend.call(prompt, system)
                backend.errors = 0  # Reset on success
                print("✓")
                return response, backend.name
                
            except Exception as e:
                backend.errors += 1
                print(f"✗ ({e})")
                
                if backend.errors >= backend.max_errors:
                    print(f"   ⚠️ Removing {backend.name} after {backend.errors} failures")
                    backend.available = False
        
        raise RuntimeError("All backends failed this round")


# === INVESTIGATION PHASES ===

@dataclass
class Phase:
    id: str
    name: str
    prompt: Optional[str]
    success_criteria: list[str] = field(default_factory=list)
    generates_diagram: bool = False


PHASES = [
    Phase(
        id="clone",
        name="🔽 Clone Repository",
        prompt=None,
    ),
    Phase(
        id="overview",
        name="📊 High-Level Overview",
        prompt="""Analyze the Bark repository structure I just cloned.

Files to examine:
{file_list}

README content:
{readme}

Give me:
1. What is Bark? (one paragraph)
2. Main components/modules identified
3. Entry points (how do you USE it?)
4. Key dependencies from requirements
5. Architecture diagram (ASCII art)

Be thorough. This is phase 1 of many.""",
        success_criteria=[
            "Identified main purpose of Bark",
            "Listed all major components/modules",
            "Found entry point functions",
            "Listed key dependencies",
            "Created ASCII architecture diagram"
        ],
        generates_diagram=True
    ),
    Phase(
        id="c4_context",
        name="🏗️ C4 Context Diagram",
        prompt="""Create a C4 CONTEXT diagram for Bark.

Show:
- Bark as the central system
- External actors (users, other systems)
- Data flows in/out

Format as ASCII art:
```
┌─────────────────────────────────────────────────┐
│                   CONTEXT                        │
├─────────────────────────────────────────────────┤
│                                                  │
│   [User] ──text──> [BARK] ──audio──> [Speaker]  │
│                       │                          │
│                       v                          │
│               [Hugging Face]                     │
│              (model weights)                     │
│                                                  │
└─────────────────────────────────────────────────┘
```

Also describe each actor and relationship.""",
        success_criteria=[
            "Identified all external actors",
            "Showed data flow directions",
            "Created ASCII C4 context diagram"
        ],
        generates_diagram=True
    ),
    Phase(
        id="c4_container",
        name="📦 C4 Container Diagram", 
        prompt="""Create a C4 CONTAINER diagram for Bark.

Based on your analysis, show the major containers (deployable units):
- Python package structure
- Model files
- Config/assets
- API layer

Files for reference:
{structure}

Format as ASCII:
```
┌────────────────── BARK ──────────────────┐
│                                           │
│  ┌─────────────┐    ┌─────────────┐      │
│  │   API       │───>│  Generation │      │
│  │ (api.py)    │    │  Pipeline   │      │
│  └─────────────┘    └──────┬──────┘      │
│                            │              │
│         ┌──────────────────┼─────────┐   │
│         v                  v         v   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │ Semantic │  │  Coarse  │  │   Fine   ││
│  │  Model   │  │  Model   │  │  Model   ││
│  └──────────┘  └──────────┘  └──────────┘│
└───────────────────────────────────────────┘
```""",
        success_criteria=[
            "Identified all containers/modules",
            "Showed dependencies between containers",
            "Created ASCII container diagram"
        ],
        generates_diagram=True
    ),
    Phase(
        id="models",
        name="🧠 Model Architecture",
        prompt="""Deep dive into Bark's MODEL architecture.

Read and analyze these files:
{model_files}

I need to understand:
1. What neural network architectures? (Transformers? CNNs?)
2. How many models? What does each do?
3. Input/output shapes and formats
4. Tokenization strategy
5. How are audio features represented?
6. Model sizes and parameter counts
7. Pre-trained checkpoints - trained on what?

Show actual class definitions. Explain each.""",
        success_criteria=[
            "Identified all neural network types",
            "Documented each model's purpose",
            "Found input/output shapes",
            "Explained tokenization",
            "Listed model sizes"
        ]
    ),
    Phase(
        id="generation",
        name="🎵 Generation Pipeline",
        prompt="""Analyze Bark's GENERATION pipeline - text → audio.

Files to examine:
{generation_files}

Explain step by step:
1. Text input → preprocessing
2. Semantic token generation
3. Coarse acoustic generation
4. Fine acoustic generation  
5. Audio waveform synthesis
6. Role of EnCodec or similar
7. Sampling strategies (temperature, top-k)

Create a FLOW DIAGRAM (ASCII) of the complete pipeline.""",
        success_criteria=[
            "Documented preprocessing steps",
            "Explained semantic generation",
            "Explained coarse generation",
            "Explained fine generation",
            "Explained audio synthesis",
            "Created pipeline flow diagram"
        ],
        generates_diagram=True
    ),
    Phase(
        id="c4_component",
        name="🔧 C4 Component Diagram",
        prompt="""Create C4 COMPONENT diagram for Bark's generation pipeline.

Show internal components of the generation container:
- Text encoder
- Semantic model
- Coarse acoustic model
- Fine acoustic model
- Audio decoder

Include:
- Data flow between components
- Key classes/functions
- Tensor shapes at each stage

ASCII format with annotations.""",
        success_criteria=[
            "Showed all internal components",
            "Documented data flow",
            "Annotated with shapes/types"
        ],
        generates_diagram=True
    ),
    Phase(
        id="encodec",
        name="🔊 Audio Codec Deep Dive",
        prompt="""Deep dive into Bark's AUDIO CODEC.

Analyze:
{codec_files}

Questions:
1. Is it EnCodec or custom?
2. Compression ratio (tokens per second)
3. Codebook sizes and structure
4. How does quantization work?
5. Decoder architecture
6. Quality vs compression tradeoffs

Compare to DAC (Descript Audio Codec) which we might use.""",
        success_criteria=[
            "Identified codec type",
            "Found compression ratio",
            "Documented codebook structure",
            "Explained quantization",
            "Compared to DAC"
        ]
    ),
    Phase(
        id="training",
        name="🏋️ Training Details",
        prompt="""Investigate how Bark was TRAINED.

Search for:
{training_files}

Also search web/papers for Bark training details.

Questions:
1. Training dataset?
2. Loss functions?
3. Training compute/time?
4. Fine-tuning capabilities?
5. How would WE train something similar?
6. Hardware requirements?

If training code isn't in repo, research it.""",
        success_criteria=[
            "Found dataset info (or noted unavailable)",
            "Documented loss functions",
            "Listed hardware requirements",
            "Outlined training approach"
        ]
    ),
    Phase(
        id="inference",
        name="⚡ Inference & Optimization",
        prompt="""Analyze inference optimizations in Bark.

Look at:
{inference_files}

Questions:
1. Batch processing support?
2. GPU memory management
3. Streaming generation?
4. Caching strategies (KV-cache?)
5. Model loading/offloading
6. Speed benchmarks?
7. ONNX/TensorRT exports?""",
        success_criteria=[
            "Documented batching",
            "Found memory management",
            "Identified caching strategies",
            "Listed any benchmarks"
        ]
    ),
    Phase(
        id="comparison",
        name="🔄 Compare to Our Architecture",
        prompt="""Compare Bark to OUR stem separator design:

OUR 5-STAGE PIPELINE:
1. Separator (Complex U-Net) - extracts mask/"bad stem"
2. Compressor (DAC VAE Encoder) - 2048x downsample, Snake activations  
3. Guide (LiLAC ControlNet) - lightweight structural guidance
4. Generator (Stable Audio DiT) - Flow Matching, RoPE, 128ch
5. Synthesizer (HiFi-GAN Decoder) - Snake activations, 2048x upsample

BARK'S COMPONENTS (from your analysis):
{bark_summary}

Compare:
1. What can we STEAL from Bark?
2. Key differences in approach
3. What does Bark do better?
4. What does our design do better?
5. Specific code/techniques to borrow
6. Architecture lessons learned""",
        success_criteria=[
            "Listed borrowable components",
            "Identified key differences",
            "Made specific recommendations",
            "Created comparison table"
        ]
    ),
    Phase(
        id="synthesis",
        name="📝 Final Synthesis",
        prompt="""Create the FINAL comprehensive document.

Synthesize EVERYTHING into actionable documentation:

1. **Executive Summary** - What IS Bark?
2. **Complete Architecture Diagram** - Full system
3. **Component Breakdown** - Each piece explained
4. **Code Snippets Worth Studying** - Key implementations
5. **What We Should Copy** - For our project
6. **What We Should Avoid** - Bark's weaknesses
7. **Implementation Roadmap** - How to build our version
8. **Open Questions** - What needs more research

Make this ACTIONABLE for building our own system.""",
        success_criteria=[
            "Created executive summary",
            "Included complete architecture diagram",
            "Documented all components",
            "Listed code to study",
            "Made specific recommendations",
            "Created implementation roadmap"
        ]
    ),
]


# === UTILITY FUNCTIONS ===

def run_cmd(cmd: str, cwd: Optional[Path] = None) -> tuple[bool, str]:
    """Run shell command."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=cwd or WORK_DIR, timeout=300
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def clone_bark() -> bool:
    """Clone the Bark repository."""
    bark_path = BARK_REPO_PATH
    
    if bark_path.exists():
        print("   Already cloned, pulling latest...")
        run_cmd("git pull", cwd=bark_path)
        return True
    
    print(f"   Cloning {BARK_REPO_URL} into {bark_path}...")
    success, output = run_cmd(
        f"git clone {BARK_REPO_URL} {bark_path}",
        cwd=bark_path.parent
    )
    
    if not success:
        print(f"   ❌ Clone failed: {output}")
        return False
    
    print("   ✅ Cloned successfully")
    return True


def get_file_list(directory: Path, extensions: set = None) -> list[str]:
    """Get all files in directory."""
    if extensions is None:
        extensions = {'.py', '.md', '.txt', '.json', '.yaml', '.yml'}
    
    files = []
    for f in directory.rglob('*'):
        if f.is_file() and f.suffix in extensions and '.git' not in str(f):
            files.append(str(f.relative_to(directory)))
    return sorted(files)


def read_file_safe(path: Path, max_chars: int = 15000) -> str:
    """Read file content safely."""
    try:
        if not path.exists():
            return f"[FILE NOT FOUND: {path}]"
        content = path.read_text(errors='ignore')
        if len(content) > max_chars:
            return content[:max_chars] + f"\n\n... [TRUNCATED - {len(content)} total chars]"
        return content
    except Exception as e:
        return f"[ERROR READING: {e}]"


def rate_thinking_difficulty(prompt: str, phase_id: str = "") -> int:
    """Heuristic difficulty rating from 1-10."""
    score = 3
    prompt_lower = prompt.lower()
    keywords = [
        "deep dive", "architecture", "compare", "model", "training",
        "pipeline", "c4", "diagram", "token", "codec", "quantiz",
        "transformer", "sampling", "inference", "optimization",
        "representation", "parameter", "checkpoint"
    ]
    for word in keywords:
        if word in prompt_lower:
            score += 1
    if len(prompt) > 2000:
        score += 2
    if len(prompt) > 4000:
        score += 2
    if phase_id in {"models", "generation", "encodec", "training", "comparison", "final"}:
        score += 2
    return max(1, min(10, score))


def _format_mcp_result(result) -> str:
    if result is None:
        return ""
    content = getattr(result, "content", None)
    structured = getattr(result, "structuredContent", None)
    if content:
        parts = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
            else:
                parts.append(str(item))
        if structured:
            parts.append(json.dumps(structured, indent=2))
        return "\n".join(p for p in parts if p)
    return str(result)


def call_deepthinking_mcp(tool_name: str, arguments: dict) -> str:
    try:
        import anyio
        from mcp import ClientSession, StdioServerParameters, stdio_client

        async def _run():
            server = StdioServerParameters(
                command=DEEPTHINKING_MCP_COMMAND,
                args=DEEPTHINKING_MCP_ARGS,
                cwd=DEEPTHINKING_MCP_CWD,
            )
            async with stdio_client(server) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    if tool_name == "__list__":
                        return await session.list_tools()
                    return await session.call_tool(tool_name, arguments or {})

        result = anyio.run(_run)
        return _format_mcp_result(result)
    except Exception as exc:
        return f"[MCP ERROR] {exc}"


def find_files_matching(directory: Path, patterns: list[str]) -> list[Path]:
    """Find files matching patterns."""
    results = []
    for pattern in patterns:
        results.extend(directory.rglob(pattern))
    return [f for f in results if f.is_file() and '.git' not in str(f)]


def load_state() -> dict:
    """Load progress state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "completed_phases": [], 
        "findings": {}, 
        "started_at": datetime.now().isoformat(),
        "backend_failures": {}
    }


def save_state(state: dict):
    """Save progress state."""
    STATE_FILE.write_text(json.dumps(state, indent=2))


def append_output(content: str, phase_name: str = ""):
    """Append to output document."""
    with open(OUTPUT_FILE, 'a') as f:
        if phase_name:
            f.write(f"\n\n---\n\n# {phase_name}\n\n")
        f.write(content)
        f.write("\n")


def check_success_criteria(response: str, criteria: list[str]) -> tuple[bool, list[str]]:
    """Check if response meets success criteria."""
    missing = []
    response_lower = response.lower()
    
    # Simple heuristic checks
    checks = {
        "diagram": ["```", "┌", "│", "└", "──", "->", "→"],
        "identified": True,  # Assume identified if response is long enough
        "documented": True,
        "listed": True,
        "explained": True,
        "created": ["```", "┌", "│"],
        "found": True,
        "showed": True,
        "compared": ["vs", "versus", "comparison", "differ"],
        "made": True,
    }
    
    for criterion in criteria:
        criterion_lower = criterion.lower()
        met = False
        
        for keyword, check in checks.items():
            if keyword in criterion_lower:
                if check is True:
                    met = len(response) > 500  # Basic length check
                elif isinstance(check, list):
                    met = any(c in response for c in check)
                break
        
        if not met:
            missing.append(criterion)
    
    return len(missing) == 0, missing


# === MAIN LOOP ===

def ralph_wiggum_loop():
    """
    🐕 "I'm learnding!"
    
    The endless loop. Keeps going through phases until everything is understood.
    """
    
    WORK_DIR.mkdir(exist_ok=True)
    
    print("=" * 70)
    print("🐕 BARK DISSECTOR - Ralph Wiggum Mode v2")
    print("   'I'm learnding!'")
    print("=" * 70)
    print(f"Target: {BARK_REPO_PATH}")
    print(f"Output: {OUTPUT_FILE}")
    print("-" * 70)
    
    # Init router with fallbacks
    print("\n🔌 Initializing LLM backends...")
    router = LLMRouter()
    
    # Load state
    state = load_state()
    
    # Init output doc if fresh
    if not OUTPUT_FILE.exists():
        OUTPUT_FILE.write_text(f"""# 🐕 Bark Architecture Dissection

**Generated by:** Bark Dissector v2 (Ralph Wiggum Mode)
**Target Repository:** {BARK_REPO_PATH} ({BARK_REPO_URL})
**Started:** {state['started_at']}
**Purpose:** Reverse engineer Bark to build our own audio generation system

---

""")
    
    bark_path = BARK_REPO_PATH
    
    # === PHASE LOOP ===
    for phase in PHASES:
        phase_id = phase.id
        phase_name = phase.name
        
        # Skip completed
        if phase_id in state["completed_phases"]:
            print(f"\n✅ {phase_name} - Already complete")
            continue
        
        print(f"\n{'='*60}")
        print(f"🔄 {phase_name}")
        print(f"{'='*60}")
        
        # === PHASE: Clone ===
        if phase_id == "clone":
            if not clone_bark():
                print("❌ Cannot proceed without repo. Exiting.")
                return
            state["completed_phases"].append(phase_id)
            save_state(state)
            continue
        
        # === BUILD CONTEXT ===
        context = {}
        
        if phase_id == "overview":
            context["file_list"] = "\n".join(get_file_list(bark_path)[:50])
            readme_path = bark_path / "README.md"
            context["readme"] = read_file_safe(readme_path, 10000)
        
        elif phase_id in ["c4_context", "c4_container"]:
            context["structure"] = "\n".join(get_file_list(bark_path)[:30])
        
        elif phase_id == "models":
            model_files = find_files_matching(bark_path, ["*model*.py", "*transformer*.py", "*gpt*.py"])
            context["model_files"] = "\n\n---\n\n".join([
                f"### {f.name}\n```python\n{read_file_safe(f, 12000)}\n```"
                for f in model_files[:8]
            ])
        
        elif phase_id in ["generation", "c4_component"]:
            gen_files = find_files_matching(bark_path, ["*generat*.py", "*sampl*.py", "*inference*.py", "api.py"])
            context["generation_files"] = "\n\n---\n\n".join([
                f"### {f.name}\n```python\n{read_file_safe(f, 12000)}\n```"
                for f in gen_files[:8]
            ])
        
        elif phase_id == "training":
            train_files = find_files_matching(bark_path, ["*train*.py", "*loss*.py", "*optim*.py"])
            context["training_files"] = "\n".join([str(f.relative_to(bark_path)) for f in train_files]) or "No training files found in repo"
        
        elif phase_id == "encodec":
            codec_files = find_files_matching(bark_path, ["*codec*.py", "*encodec*.py", "*quantiz*.py", "*audio*.py"])
            context["codec_files"] = "\n\n---\n\n".join([
                f"### {f.name}\n```python\n{read_file_safe(f, 12000)}\n```"
                for f in codec_files[:6]
            ]) or "No codec files found - may use external library"
        
        elif phase_id == "inference":
            inf_files = find_files_matching(bark_path, ["*infer*.py", "*run*.py", "*predict*.py", "api.py", "__init__.py"])
            context["inference_files"] = "\n".join([str(f.relative_to(bark_path)) for f in inf_files])
        
        elif phase_id == "comparison":
            context["bark_summary"] = "\n".join([
                f"- {pid}: {state['findings'].get(pid, 'Analysis pending')[:500]}"
                for pid in ["overview", "models", "generation", "encodec"]
            ])
        
        # === FORMAT PROMPT ===
        prompt_template = phase.prompt
        try:
            prompt = prompt_template.format(**context)
        except (KeyError, TypeError):
            prompt = prompt_template or "Continue analysis."

        # === CALL LLM WITH RETRIES ===
        system = """You are reverse-engineering the Bark audio generation model.
Goal: Understand EVERYTHING so we can build our own similar system.
Be extremely thorough. Include code snippets. Create diagrams when asked.
This documentation will be used to build our own audio generation system.
Web tools are disabled unless ALLOW_WEB_TOOLS=true; rely only on local files."""

        difficulty = rate_thinking_difficulty(prompt, phase_id)
        print(f"   🧠 Thinking difficulty: {difficulty}/10")
        if difficulty > 5:
            deepthinking_context = call_deepthinking_mcp(
                "deepthinking_analyze",
                {
                    "thought": prompt,
                    "preset": "comprehensive_analysis",
                    "mergeStrategy": "dialectical",
                    "context": system,
                    "timeoutPerMode": 45000,
                }
            )
            if deepthinking_context:
                trimmed = deepthinking_context[:6000]
                prompt = f"DeepThinking MCP analysis:\n{trimmed}\n\n---\n\n{prompt}"
        
        max_attempts = 3
        full_response = ""
        backend_used = ""
        
        for attempt in range(max_attempts):
            try:
                print(f"   📡 Attempt {attempt + 1}/{max_attempts}")
                full_response, backend_used = router.call(prompt, system)
                break
            except Exception as e:
                print(f"   ❌ Attempt failed: {e}")
                if attempt < max_attempts - 1:
                    print("   ⏳ Waiting 10s before retry...")
                    time.sleep(10)
        
        if not full_response:
            print(f"   ⚠️ Phase failed after {max_attempts} attempts, skipping...")
            continue
        
        # === CHECK SUCCESS CRITERIA ===
        if phase.success_criteria:
            passed, missing = check_success_criteria(full_response, phase.success_criteria)
            if not passed and missing:
                print(f"   ⚠️ Missing criteria: {missing[:3]}")
                # Try one follow-up
                followup = f"Your response is missing: {', '.join(missing)}. Please address these specifically."
                try:
                    extra, _ = router.call(followup, system)
                    full_response += "\n\n---\n\n## Additional Details\n\n" + extra
                except:
                    pass
        
        # === SAVE RESULTS ===
        state["findings"][phase_id] = full_response[:2000]
        state["completed_phases"].append(phase_id)
        save_state(state)
        
        # Write to output
        append_output(full_response, phase_name)
        append_output(f"\n*Backend: {backend_used}*")
        
        print(f"   ✅ {phase_name} complete!")
        
        time.sleep(2)
    
    # === COMPLETE ===
    print("\n" + "=" * 70)
    print("🎉 DISSECTION COMPLETE!")
    print("=" * 70)
    print(f"📄 Full report: {OUTPUT_FILE}")
    
    append_output(f"""
---

## 📊 Dissection Complete

- **Finished:** {datetime.now().isoformat()}
- **Phases completed:** {len(state['completed_phases'])}

*Generated by Bark Dissector v2 - Ralph Wiggum Mode*
*"I'm learnding!"*
""", "✅ Completion")


def main():
    if not XAI_API_KEY:
        print("❌ No API keys found!")
        print("   - export XAI_API_KEY=xai-...")
        sys.exit(1)
    
    ralph_wiggum_loop()


if __name__ == "__main__":
    main()
