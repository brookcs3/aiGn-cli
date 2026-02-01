#!/usr/bin/env python3
import argparse
import fnmatch
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx

from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search, x_search, code_execution


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


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    config = json.loads(path.read_text())

    def _coerce_bool(value, default=False):
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        return default

    defaults = {
        "difficulty_threshold": 6,
        "output_format": "md",
        "tools": ["web_search", "x_search", "code_execution"],
        "phases": [
            "overview",
            "architecture",
            "core_modules",
            "pipeline",
            "training",
            "comparison",
            "final",
        ],
        "prompt_override_dir": None,
        "repomix": [],
        "ignore": [
            ".git",
            "node_modules",
            "dist",
            "build",
            ".venv",
            "__pycache__",
            ".DS_Store",
        ],
        "max_files": 60,
        "max_chars": 12000,
        "context_budget_chars": 12000 * 4,
        "max_tokens": 8192,
        "max_retries": 3,
        "retry_backoff_sec": 5,
        "force": False,
        "mcp_enabled": True,
        "mcp_inject": True,
        "phase_context_patterns": {},
        "system_prompt": (
            "You are a senior systems analyst producing a structured, actionable report. "
            "Be thorough and concise. Include diagrams where requested."
        ),
    }
    for key, value in defaults.items():
        config.setdefault(key, value)

    if isinstance(config.get("tools"), str):
        config["tools"] = [t for t in config["tools"].split(",") if t]
    if isinstance(config.get("phases"), str):
        config["phases"] = [p for p in config["phases"].split(",") if p]
    if isinstance(config.get("ignore"), str):
        config["ignore"] = [p for p in config["ignore"].split(",") if p]

    config["difficulty_threshold"] = int(config.get("difficulty_threshold", 6))
    config["max_files"] = int(config.get("max_files", 60))
    config["max_chars"] = int(config.get("max_chars", 12000))
    config["context_budget_chars"] = int(config.get("context_budget_chars", defaults["context_budget_chars"]))
    config["max_tokens"] = int(config.get("max_tokens", defaults["max_tokens"]))
    config["max_retries"] = int(config.get("max_retries", defaults["max_retries"]))
    config["retry_backoff_sec"] = int(config.get("retry_backoff_sec", defaults["retry_backoff_sec"]))

    config["force"] = _coerce_bool(config.get("force", defaults["force"]))
    config["mcp_enabled"] = _coerce_bool(config.get("mcp_enabled", defaults["mcp_enabled"]))
    config["mcp_inject"] = _coerce_bool(config.get("mcp_inject", defaults["mcp_inject"]))

    output_format = str(config.get("output_format", "md")).strip().lower()
    if output_format not in {"md", "json", "both"}:
        output_format = "md"
    config["output_format"] = output_format

    if not isinstance(config.get("repomix"), list):
        config["repomix"] = []
    if not isinstance(config.get("phase_context_patterns"), dict):
        config["phase_context_patterns"] = {}

    for key in ("target_path", "output_dir", "model"):
        if not config.get(key):
            raise ValueError(f"Missing required config key: {key}")

    return config


def new_state() -> dict:
    return {
        "started_at": datetime.now().isoformat(),
        "completed_phases": [],
        "artifacts_dir": None,
        "phase_status": {},
        "phase_attempts": {},
    }


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return new_state()


def save_state(path: Path, state: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def rate_thinking_difficulty(prompt: str) -> int:
    score = 3
    lower = prompt.lower()
    keywords = [
        "architecture",
        "pipeline",
        "training",
        "inference",
        "token",
        "codec",
        "diagram",
        "c4",
        "analysis",
        "compare",
    ]
    for word in keywords:
        if word in lower:
            score += 1
    if len(prompt) > 2000:
        score += 2
    if len(prompt) > 4000:
        score += 2
    return max(1, min(10, score))


def read_file_safe(path: Path, max_chars: int = 12000) -> str:
    try:
        content = path.read_text(errors="ignore")
        if len(content) > max_chars:
            return content[:max_chars] + f"\n\n... [TRUNCATED - {len(content)} total chars]"
        return content
    except Exception as exc:
        return f"[ERROR READING {path}: {exc}]"


class ContextLoader:
    def __init__(self, root: Path, ignore: List[str], max_files: int, max_chars: int, budget_chars: int):
        self.root = root
        self.ignore = ignore
        self.max_files = max_files
        self.max_chars = max_chars
        self.budget_chars = budget_chars

    def _is_ignored(self, path: Path) -> bool:
        text = str(path)
        rel = str(path.relative_to(self.root)) if self.root in path.parents else text
        for token in self.ignore:
            token = token.strip()
            if not token:
                continue
            if fnmatch.fnmatch(rel, token) or fnmatch.fnmatch(text, token):
                return True
            if token in text:
                return True
        return False

    def index_files(self) -> List[Path]:
        files = []
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            if self._is_ignored(path):
                continue
            if path.suffix.lower() in {".pyc", ".pyo", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".wav", ".mp3"}:
                continue
            files.append(path)
        files.sort(key=lambda p: p.stat().st_size, reverse=True)
        return files

    def load_top_files(self, patterns: Optional[List[str]] = None) -> str:
        files = self.index_files()
        if patterns:
            selected = []
            for pattern in patterns:
                selected.extend([p for p in files if p.match(pattern)])
            if selected:
                files = selected
        files = files[: self.max_files]
        sections = []
        remaining = self.budget_chars
        for path in files:
            if remaining <= 0:
                break
            content = read_file_safe(path, min(self.max_chars, remaining))
            remaining -= len(content)
            sections.append(f"### {path.relative_to(self.root)}\n{content}")
        return "\n\n".join(sections)


@dataclass
class Phase:
    id: str
    name: str
    prompt: str
    success_criteria: List[str] = field(default_factory=list)
    context_patterns: List[str] = field(default_factory=list)


PHASES = [
    Phase(
        id="overview",
        name="Overview",
        prompt=(
            "Analyze the target repository structure.\n\n"
            "Files (sample):\n{file_list}\n\nREADME:\n{readme}\n\n"
            "Provide:\n"
            "1) What is this project?\n"
            "2) Main components/modules\n"
            "3) Entry points / usage\n"
            "4) Key dependencies\n"
            "5) Quick ASCII architecture diagram\n"
        ),
        success_criteria=[
            "Identified main purpose",
            "Listed components",
            "Found entry points",
            "Created ASCII diagram",
        ],
    ),
    Phase(
        id="architecture",
        name="Architecture",
        prompt=(
            "Create C4 context + container diagrams for the project.\n\n"
            "Use the following code/context:\n{context}\n\n"
            "Provide diagrams and brief explanations."
        ),
        success_criteria=["Created ASCII context diagram", "Created ASCII container diagram"],
    ),
    Phase(
        id="core_modules",
        name="Core Modules",
        prompt=(
            "Deep dive the core modules. Identify key classes/functions and data flow.\n\n"
            "Context:\n{context}"
        ),
        success_criteria=["Documented core modules", "Explained data flow"],
    ),
    Phase(
        id="pipeline",
        name="Pipeline",
        prompt=(
            "Describe the end-to-end pipeline, inputs, outputs, and transformations.\n\n"
            "Context:\n{context}\n\n"
            "Include an ASCII flow diagram."
        ),
        success_criteria=["Created flow diagram", "Explained end-to-end pipeline"],
    ),
    Phase(
        id="training",
        name="Training/Inference",
        prompt=(
            "If ML-related, analyze training/inference workflows, configs, and checkpoints.\n\n"
            "Context:\n{context}"
        ),
        success_criteria=["Documented training/inference"],
    ),
    Phase(
        id="comparison",
        name="Comparison/Recommendations",
        prompt=(
            "Compare this system to the target goals and provide recommendations.\n\n"
            "Summary so far:\n{summary}"
        ),
        success_criteria=["Provided recommendations"],
    ),
    Phase(
        id="final",
        name="Final Synthesis",
        prompt=(
            "Create a complete synthesis document with architecture, key learnings, "
            "risks, and next steps.\n\n"
            "Summary so far:\n{summary}"
        ),
        success_criteria=["Created final synthesis"],
    ),
]


class GrokRouter:
    def __init__(self, model: str, tools: List[str], api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.client = Client(api_key=api_key, timeout=3600)
        self.model = model
        self.tools = tools
        self.base_url = (
            base_url
            or os.environ.get("XAI_API_BASE")
            or os.environ.get("XAI_API_URL")
            or "https://api.x.ai/v1"
        )

    def _tools_list(self):
        available = []
        if "web_search" in self.tools:
            available.append(web_search())
        if "x_search" in self.tools:
            available.append(x_search())
        if "code_execution" in self.tools:
            available.append(code_execution())
        return available

    def _call_http(self, prompt: str, system_prompt: str, max_tokens: int) -> str:
        if not self.api_key:
            raise RuntimeError("Missing XAI_API_KEY for HTTP fallback")
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=3600) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content).strip()
        return str(content).strip()

    def call(self, prompt: str, system_prompt: str, max_tokens: int) -> str:
        print("   🔌 Trying xai_sdk...", end=" ", flush=True)
        try:
            chat = self.client.chat.create(
                model=self.model,
                max_tokens=max_tokens,
                tools=self._tools_list(),
            )
            chat.append(system(system_prompt))
            chat.append(user(prompt))
            response = None
            content_parts: List[str] = []
            for response, chunk in chat.stream():
                for tool_call in chunk.tool_calls:
                    print(f"\n   🧰 Tool call: {tool_call.function.name} {tool_call.function.arguments}")
                if chunk.content:
                    content_parts.append(chunk.content)
            print("✓")
            return "".join(content_parts).strip()
        except Exception as exc:
            print(f"✗ ({exc})")
            print("   🔌 Trying xai_http...", end=" ", flush=True)
            result = self._call_http(prompt, system_prompt, max_tokens)
            print("✓")
            return result


class DeepThinkingMCP:
    def __init__(self):
        self.command = os.environ.get("DEEPTHINKING_MCP_COMMAND", "node")
        self.args = os.environ.get(
            "DEEPTHINKING_MCP_ARGS",
            "/Users/cameronbrooks/deepthinking-mcp/dist/index.js",
        ).split()
        self.cwd = os.environ.get("DEEPTHINKING_MCP_CWD", "/Users/cameronbrooks/deepthinking-mcp")
        self._tools_cache: Optional[List[str]] = None

    def _format_result(self, result) -> str:
        if result is None:
            return ""
        content = getattr(result, "content", None)
        structured = getattr(result, "structuredContent", None)
        if content:
            parts = []
            for item in content:
                text = getattr(item, "text", None)
                parts.append(text if text else str(item))
            if structured:
                parts.append(json.dumps(structured, indent=2))
            return "\n".join(p for p in parts if p)
        return str(result)

    def list_tools(self) -> List[str]:
        if self._tools_cache is not None:
            return self._tools_cache
        try:
            import anyio
            from mcp import ClientSession, StdioServerParameters, stdio_client

            async def _run():
                server = StdioServerParameters(
                    command=self.command,
                    args=self.args,
                    cwd=self.cwd,
                )
                async with stdio_client(server) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        items = getattr(tools, "tools", None)
                        if items is None and isinstance(tools, dict):
                            items = tools.get("tools", [])
                        names = []
                        for item in items:
                            name = getattr(item, "name", None)
                            if not name and isinstance(item, dict):
                                name = item.get("name")
                            if name:
                                names.append(name)
                        return names

            self._tools_cache = [t for t in anyio.run(_run) if t]
        except Exception:
            self._tools_cache = []
        return self._tools_cache

    def call(self, tool: str, arguments: dict) -> str:
        try:
            import anyio
            from mcp import ClientSession, StdioServerParameters, stdio_client

            async def _run():
                server = StdioServerParameters(
                    command=self.command,
                    args=self.args,
                    cwd=self.cwd,
                )
                async with stdio_client(server) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        return await session.call_tool(tool, arguments)

            available = self.list_tools()
            if available and tool not in available:
                if "deepthinking" in available:
                    arguments = {"tool": tool, **arguments}
                    tool = "deepthinking"
                else:
                    return f"[MCP ERROR] tool '{tool}' not available"
            result = anyio.run(_run)
            return self._format_result(result)
        except Exception as exc:
            return f"[MCP ERROR] {exc}"

    def recommend_mode(self, characteristics: dict) -> str:
        available = self.list_tools()
        if "deepthinking_session" in available:
            return self.call("deepthinking_session", {"action": "recommend_mode", **characteristics})
        if "deepthinking" in available:
            payload = {"action": "recommend_mode", **characteristics}
            return self.call("deepthinking", payload)
        return ""

    def analyze(self, payload: dict) -> str:
        available = self.list_tools()
        if "deepthinking_analyze" in available:
            return self.call("deepthinking_analyze", payload)
        if "deepthinking" in available:
            return self.call("deepthinking", payload)
        return ""


class Dissector:
    def __init__(self, config: dict):
        self.config = config
        self.target = Path(config["target_path"])
        self.output_dir = Path(config["output_dir"])
        self.state_path = Path(config.get("state_file") or (self.output_dir / ".dissect_state.json"))
        self.artifacts_dir = self.output_dir / "artifacts"
        self.router = GrokRouter(
            config["model"],
            config["tools"],
            os.environ.get("XAI_API_KEY", ""),
        )
        self.mcp = DeepThinkingMCP()
        self.max_tokens = config["max_tokens"]
        self.max_retries = config["max_retries"]
        self.retry_backoff_sec = config["retry_backoff_sec"]
        self.force = config["force"]
        self.mcp_enabled = config["mcp_enabled"]
        self.mcp_inject = config["mcp_inject"]

    def ensure_output_dir(self, resume: bool = False):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if resume or self.force:
            return
        existing = [p for p in self.output_dir.iterdir()]
        if existing:
            raise RuntimeError(
                f"Output dir not empty: {self.output_dir}. Use --force or choose a new output_dir."
            )

    def prepare(self):
        missing = []
        if not os.environ.get("XAI_API_KEY"):
            missing.append("XAI_API_KEY")
        if missing:
            raise RuntimeError(f"Missing env vars: {', '.join(missing)}")
        if not self.target.exists():
            raise FileNotFoundError(f"Target path not found: {self.target}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print("   📋 Prepare summary:")
        print(f"      Target: {self.target}")
        print(f"      Output: {self.output_dir}")
        print(f"      Model: {self.config['model']}")
        print(f"      Phases: {', '.join(self.config['phases'])}")
        if self.config.get("prompt_override_dir"):
            if not Path(self.config["prompt_override_dir"]).exists():
                print("   ⚠️  Prompt override dir not found.")

        if self.mcp_enabled:
            tools = self.mcp.list_tools()
            if not tools:
                print("   ⚠️  DeepThinking MCP not available or returned no tools.")
            else:
                print(f"   🧰 DeepThinking MCP tools: {', '.join(tools[:8])}" + ("..." if len(tools) > 8 else ""))

        for repomix in self.config.get("repomix", []):
            path = repomix.get("path")
            output = repomix.get("output")
            ignore = repomix.get("ignore", "")
            if not path or not output:
                continue
            if not Path(path).exists():
                raise FileNotFoundError(f"repomix path not found: {path}")
            cmd = ["repomix", path, "-o", output]
            if ignore:
                cmd.extend(["--ignore", ignore])
            subprocess.run(cmd, check=True)

    def run(self, resume: bool = False):
        self.ensure_output_dir(resume=resume)
        loader = ContextLoader(
            self.target,
            self.config["ignore"],
            self.config["max_files"],
            self.config["max_chars"],
            self.config["context_budget_chars"],
        )
        state = load_state(self.state_path) if resume else new_state()
        state["artifacts_dir"] = str(self.artifacts_dir)
        save_state(self.state_path, state)

        phase_map = {p.id: p for p in PHASES}
        phases = [phase_map[p] for p in self.config["phases"] if p in phase_map]
        phase_outputs = []
        for phase in phases:
            if phase.id in state["completed_phases"]:
                continue

            print(f"\n=== {phase.name} ===")
            state["phase_status"][phase.id] = "running"
            save_state(self.state_path, state)

            prompt_override = None
            if self.config.get("prompt_override_dir"):
                override_path = Path(self.config["prompt_override_dir"]) / f"{phase.id}.txt"
                if override_path.exists():
                    prompt_override = override_path.read_text(errors="ignore")

            context = ""
            if phase.id == "overview":
                file_list = "\n".join(
                    [str(p.relative_to(self.target)) for p in loader.index_files()[:50]]
                )
                readme_path = self.target / "README.md"
                readme = read_file_safe(readme_path, 12000)
                prompt = phase.prompt.format(file_list=file_list, readme=readme)
            elif phase.id in {"architecture", "core_modules", "pipeline", "training"}:
                patterns = self.config.get("phase_context_patterns", {}).get(phase.id)
                context = loader.load_top_files(patterns)
                prompt = phase.prompt.format(context=context)
            else:
                summary_text = "\n\n".join(
                    f"[{item['phase']}]\n{item['response'][:1500]}" for item in phase_outputs
                )
                prompt = phase.prompt.format(summary=summary_text)

            if prompt_override:
                prompt = prompt_override

            difficulty = rate_thinking_difficulty(prompt)
            print(f"   🧠 Thinking difficulty: {difficulty}/10")

            mcp_output = ""
            if self.mcp_enabled and difficulty > self.config["difficulty_threshold"]:
                characteristics = {
                    "problemCharacteristics": {
                        "complexity": "medium",
                        "domain": "software engineering",
                        "hasAlternatives": True,
                        "hasIncompleteInfo": True,
                        "multiAgent": False,
                        "requiresExplanation": True,
                        "requiresProof": False,
                        "requiresQuantification": False,
                        "timeDependent": True,
                        "uncertainty": "medium",
                    }
                }
                recommend = self.mcp.recommend_mode(characteristics)
                analysis = self.mcp.analyze(
                    {
                        "thought": prompt,
                        "preset": "comprehensive_analysis",
                        "mergeStrategy": "dialectical",
                        "timeoutPerMode": 60000,
                    }
                )
                mcp_output = "\n\n".join(p for p in [recommend, analysis] if p)
                if self.mcp_inject and mcp_output:
                    prompt = f"DeepThinking MCP context:\n{mcp_output}\n\n---\n\n{prompt}"

            system_prompt = self.config["system_prompt"]

            attempt = 1
            response = ""
            while attempt <= self.max_retries:
                print(f"   📡 Attempt {attempt}/{self.max_retries}")
                try:
                    response = self.router.call(prompt, system_prompt, self.max_tokens)
                    break
                except Exception as exc:
                    print(f"   ✗ ({exc})")
                    time.sleep(self.retry_backoff_sec)
                    attempt += 1
            state["phase_attempts"][phase.id] = attempt

            criteria_result = self.check_success(response, phase.success_criteria)

            self.write_artifacts(phase.id, prompt, context, response, mcp_output, criteria_result)

            phase_outputs.append({"phase": phase.id, "response": response})
            state["completed_phases"].append(phase.id)
            state["phase_status"][phase.id] = "completed"
            save_state(self.state_path, state)

        self.write_report(phase_outputs)

    def check_success(self, response: str, criteria: List[str]) -> dict:
        missing = []
        lower = response.lower()
        for criterion in criteria:
            if "diagram" in criterion.lower():
                if "┌" not in response and "```" not in response:
                    missing.append(criterion)
            elif len(lower) < 500:
                missing.append(criterion)
        return {"passed": len(missing) == 0, "missing": missing}

    def write_artifacts(
        self,
        phase_id: str,
        prompt: str,
        context: str,
        response: str,
        mcp_output: str,
        criteria: dict,
    ):
        base = self.artifacts_dir / f"phase_{phase_id}"
        base.mkdir(parents=True, exist_ok=True)
        (base / "prompt.txt").write_text(prompt)
        (base / "context.txt").write_text(context or "")
        (base / "response.txt").write_text(response or "")
        if mcp_output:
            (base / "mcp.txt").write_text(mcp_output)
        (base / "criteria.json").write_text(json.dumps(criteria, indent=2))

    def write_report(self, phase_outputs: List[dict]):
        report_md = self.output_dir / "report.md"
        report_json = self.output_dir / "report.json"

        md_sections = []
        for item in phase_outputs:
            md_sections.append(f"# {item['phase']}\n\n{item['response']}")
        report_md.write_text("\n\n".join(md_sections).strip())
        report_json.write_text(json.dumps({"phases": phase_outputs}, indent=2))
        fmt = self.config["output_format"]
        if fmt == "md":
            report_json.unlink(missing_ok=True)
        elif fmt == "json":
            report_md.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config)
    _load_env_file(config_path.parent / ".env")
    _load_from_zshrc(Path.home() / ".zshrc")

    config = load_config(config_path)
    if args.force:
        config["force"] = True

    dissector = Dissector(config)
    if args.prepare:
        dissector.prepare()
        return 0

    dissector.run(resume=args.resume)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
