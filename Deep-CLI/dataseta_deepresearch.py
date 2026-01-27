#!/usr/bin/env python3
"""
AI Stem Separator Dataset Audit & Cross-Reference Tool v4.0
============================================================

Cross-references the generated dataset scaffold against the ml-ops phase
implementations using Grok with a 2M token context window.

This script performs a "Ralph Wiggum" multi-pass audit:
1. Pass 1: Extract interface contracts from ml-ops phases
2. Pass 2: Analyze dataset scaffold for compatibility
3. Pass 3: Generate comprehensive audit report with fixes

Features:
- 2M token extended context window (full repomix ingestion)
- Multi-pass analysis for thorough cross-referencing
- Automatic fix generation with complete replacement files

Usage:
    python dataset_audit.py [--output-dir <dir>]

Environment Variables:
    XAI_API_KEY: Your xAI API key (required)

Author: AI Stem Separator Dataset Audit Tool
Version: 4.0.0
"""

from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search, x_search, code_execution
import argparse
import os
import sys
import json
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Sequence
from datetime import datetime
from dataclasses import dataclass, field
import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Base project directory
def _resolve_project_root() -> Path:
    env_root = os.environ.get("AI_STEM_PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    script_path = Path(__file__).resolve()
    if len(script_path.parents) >= 4:
        return script_path.parents[3]

    return Path.cwd().resolve()


PROJECT_ROOT = _resolve_project_root()
DATASET_DIR = PROJECT_ROOT / "dataset"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# Default output for audit report (third-pass isolation)
DEFAULT_AUDIT_OUTPUT = OUTPUTS_DIR / "third_pass" / "dataset_audit_report.md"

# Grok API Configuration - Using 2M context
MODEL_NAME = "grok-4-1-fast-reasoning"
MAX_OUTPUT_TOKENS = 16000  # Output token limit
MAX_CONTEXT_TOKENS = 2000000  # 2M input context

# Retry configuration
RETRY_ATTEMPTS = 3
RETRY_DELAY = 5
RATE_LIMIT_DELAY = 60

# =============================================================================
# REPOMIX FILE PATHS
# =============================================================================

REPOMIX_PHASE_PATHS = {
    "phase1": OUTPUTS_DIR / "repomix_phase1.md",
    "phase2": OUTPUTS_DIR / "repomix_phase2.md",
    "phase3": OUTPUTS_DIR / "repomix_phase3.md",
    "phase4": OUTPUTS_DIR / "repomix_phase4.md",
    "phase5": OUTPUTS_DIR / "repomix_phase5.md",
}
REPOMIX_DATASET_PATH = OUTPUTS_DIR / "repomix_dataset.md"


def _validate_dataset_dir(dataset_dir: Path) -> Path:
    """Ensure dataset directory exists with expected scaffold folders."""
    resolved_dir = dataset_dir.expanduser().resolve()
    if not resolved_dir.exists():
        raise FileNotFoundError(
            f"Dataset directory not found: {resolved_dir}. "
            "Provide --dataset-dir or set --project-root correctly."
        )
    if not resolved_dir.is_dir():
        raise FileNotFoundError(
            f"Dataset directory is not a folder: {resolved_dir}. "
            "Provide --dataset-dir or set --project-root correctly."
        )

    required_subdirs = ["configs", "src", "scripts"]
    missing = [name for name in required_subdirs if not (resolved_dir / name).is_dir()]
    if missing:
        missing_list = ", ".join(missing)
        raise FileNotFoundError(
            f"Dataset directory is missing required folders: {missing_list}. "
            f"Expected to find {', '.join(required_subdirs)} under {resolved_dir}."
        )

    return resolved_dir

# =============================================================================
# DESIGN DOC SPECS (Canonical Reference)
# =============================================================================

DESIGN_SPECS = {
    "separator": {
        "name": "Separator (Discriminative Prior)",
        "variant": "Custom Complex U-Net (Modified QSCNet/SCNet)",
        "input": "Stereo Complex Spectrograms (or Magnitude with Phase)",
        "architecture": {
            "type": "Convolutional Encoder-Decoder",
            "conv_block": "DoubleConv (Conv3x3 → BN → ReLU)",
            "pooling": "2x2 MaxPooling",
            "output": "Structural mask / bad stem",
        },
        "audio_specs": {
            "sample_rate": 44100,
            "n_fft": 4096,
            "hop_length": 1024,
            "channels": 2,
        },
    },
    "compressor": {
        "name": "Compressor (VAE Encoder)",
        "variant": "1D Fully Convolutional Snake Encoder (DAC-Style)",
        "input": "Raw Stereo Waveform",
        "architecture": {
            "type": "1D Convolutional Downsampling Stack",
            "compression_ratio": 2048,
            "latent_channels": 64,
            "latent_rate_hz": 21.5,  # 44100 / 2048
            "activation": "Snake (f(x) = x + (1/α)*sin²(αx))",
            "encoder_rates": [4, 8, 8, 8],  # Product = 2048
        },
        "audio_specs": {
            "sample_rate": 44100,
            "channels": 2,
        },
    },
    "guide": {
        "name": "Guide (Control Mechanism)",
        "variant": "LiLAC (Lightweight Latent ControlNet)",
        "input": "64-channel latent tensor from bad stem",
        "architecture": {
            "type": "Lightweight parallel encoder",
            "wraps": "Frozen DiT blocks",
            "head_tail": "Identity Convolutions",
            "residuals": "Zero-initialized layers",
            "features_extracted": ["rhythm", "melody", "transients"],
            "parameter_reduction": "80-90% vs standard ControlNet",
        },
    },
    "generator": {
        "name": "Generator (Diffusion Transformer)",
        "variant": "1D DiT with RoPE and Flow Matching (Stable Audio Open)",
        "input": "128 channels (64 noise + 64 guide) + T5 text embeddings",
        "architecture": {
            "type": "Transformer backbone",
            "positional_encoding": "RoPE (Rotary Positional Embeddings)",
            "text_conditioning": "Cross-attention with T5",
            "timing_conditioning": "Prepended embeddings",
            "objective": "Rectified Flow (v-prediction)",
            "max_duration_seconds": 47,
            "backbone_state": "Frozen (LiLAC trains adapters only)",
        },
    },
    "synthesizer": {
        "name": "Synthesizer (VAE Decoder)",
        "variant": "1D HiFi-GAN Style Decoder with Snake Activations",
        "input": "Cleaned 64-channel latents from DiT",
        "architecture": {
            "type": "1D Transposed Convolutional Upsampling Stack",
            "upsample_ratio": 2048,
            "activation": "Snake",
            "final_activation": None,  # No tanh
            "training": "Adversarial Loss (Discriminators)",
            "decoder_rates": [8, 8, 8, 4],  # Mirror of encoder
        },
        "audio_specs": {
            "sample_rate": 44100,
            "channels": 2,
        },
    },
}


# =============================================================================
# GROK API CLIENT
# =============================================================================

class GrokClient:
    """xAI Grok client configured for a 2M context window."""
    
    def __init__(self):
        self.api_key = os.environ.get('XAI_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "XAI_API_KEY environment variable is not set.\n"
                "Please set it using:\n"
                "  export XAI_API_KEY='your-api-key-here'"
            )
        
        self.client = Client(api_key=self.api_key, timeout=3600)
        self.model = MODEL_NAME
        
        logger.info(f"Grok client initialized - Model: {self.model}")
        logger.info(f"Context window: {MAX_CONTEXT_TOKENS:,} tokens (2M)")
    
    def analyze(self, prompt: str, system_prompt: str = None,
                max_tokens: int = None) -> Tuple[str, Dict]:
        """Send analysis request to Grok with 2M context."""
        
        last_error = None
        
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                logger.info(f"Sending request to Grok (attempt {attempt})...")
                chat = self.client.chat.create(
                    model=self.model,
                    max_tokens=max_tokens or MAX_OUTPUT_TOKENS,
                    tools=[web_search(), x_search(), code_execution()],
                )
                if system_prompt:
                    chat.append(system(system_prompt))
                chat.append(user(prompt))
                
                response = chat.sample()
                
                content = getattr(response, "content", "") or ""
                if not content:
                    raise ValueError("Empty response received from API")
                
                usage = getattr(response, "usage", None)
                usage_stats = {
                    "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                    "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
                    "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
                    "model": self.model,
                }
                
                citations = getattr(response, "citations", None)
                if citations:
                    usage_stats["citations_count"] = len(citations)
                
                logger.info(
                    "Response received: "
                    f"{usage_stats['input_tokens']:,} in, "
                    f"{usage_stats['output_tokens']:,} out"
                )
                
                return content, usage_stats
                
            except Exception as e:
                last_error = e
                if attempt < RETRY_ATTEMPTS:
                    logger.warning(f"Error: {type(e).__name__}: {e}. Retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
        
        raise RuntimeError(f"Failed after {RETRY_ATTEMPTS} attempts. Last error: {last_error}")


# =============================================================================
# FILE LOADER
# =============================================================================

class FileLoader:
    """Load and validate repomix files."""
    
    def __init__(self):
        self.loaded_files: Dict[str, str] = {}
        self.file_sizes: Dict[str, int] = {}
        self.missing_files: List[str] = []
        self.repomix_metadata: Dict[str, Dict[str, Any]] = {}
        self.repomix_freshness: Dict[str, Any] = {}
    
    def load_all(self) -> Dict[str, str]:
        """Load all required files, fail fast if critical files missing."""
        logger.info("Loading repomix files...")
        
        # Load repomix files (critical)
        for name, path in REPOMIX_PHASE_PATHS.items():
            content = self._load_file(path, critical=True)
            if content:
                self.loaded_files[f"repomix_{name}"] = content
                self.file_sizes[f"repomix_{name}"] = len(content)

        dataset_content = self._load_file(REPOMIX_DATASET_PATH, critical=True)
        if dataset_content:
            self.loaded_files["repomix_dataset"] = dataset_content
            self.file_sizes["repomix_dataset"] = len(dataset_content)
        
        # Verify we have minimum required files
        if self.missing_files:
            missing_critical = [f for f in self.missing_files if "repomix" in f]
            if missing_critical:
                raise FileNotFoundError(
                    f"Critical files missing, cannot proceed:\n" +
                    "\n".join(f"  - {f}" for f in missing_critical)
                )
        
        # Report loading statistics
        total_chars = sum(self.file_sizes.values())
        estimated_tokens = int(total_chars / 4)  # ~4 chars per token
        
        logger.info(f"Loaded {len(self.loaded_files)} files")
        logger.info(f"Total size: {total_chars:,} chars (~{estimated_tokens:,} tokens)")
        
        for name, size in sorted(self.file_sizes.items()):
            logger.info(f"  {name}: {size:,} chars")
        
        if estimated_tokens > MAX_CONTEXT_TOKENS * 0.8:
            logger.warning(f"Content size approaching context limit!")

        self._check_repomix_freshness()
        
        return self.loaded_files
    
    def _load_file(self, path: Path, critical: bool = False) -> Optional[str]:
        """Load a single file."""
        try:
            if not path.exists():
                self.missing_files.append(str(path))
                if critical:
                    logger.error(f"Critical file not found: {path}")
                else:
                    logger.warning(f"Optional file not found: {path}")
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.debug(f"Loaded: {path} ({len(content):,} chars)")
            return content
            
        except Exception as e:
            logger.error(f"Error loading {path}: {e}")
            self.missing_files.append(str(path))
            return None

    def _record_repomix_metadata(self, name: str, path: Path, content: str) -> None:
        try:
            stat = path.stat()
        except OSError as exc:
            logger.warning(f"Unable to stat repomix file {path}: {exc}")
            return

        self.repomix_metadata[name] = {
            "path": str(path),
            "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "mtime_epoch": stat.st_mtime,
            "sha256": self._hash_file(path),
            "size_bytes": stat.st_size,
            "size_chars": len(content),
        }

    def _hash_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _latest_mtime_in_dir(self, directory: Path) -> Optional[float]:
        latest_mtime: Optional[float] = None
        for root, _, files in os.walk(directory):
            for filename in files:
                file_path = Path(root) / filename
                try:
                    mtime = file_path.stat().st_mtime
                except OSError:
                    continue
                if latest_mtime is None or mtime > latest_mtime:
                    latest_mtime = mtime
        return latest_mtime

    def _check_repomix_freshness(self) -> None:
        critical_dirs = {
            "dataset/src": DATASET_DIR / "src",
            "ml-ops": PROJECT_ROOT / "ml-ops",
        }

        critical_mtimes: Dict[str, float] = {}
        for label, directory in critical_dirs.items():
            if not directory.exists():
                continue
            latest = self._latest_mtime_in_dir(directory)
            if latest is not None:
                critical_mtimes[label] = latest

        stale_inputs: List[str] = []
        if critical_mtimes:
            newest_source_mtime = max(critical_mtimes.values())
            for name, meta in self.repomix_metadata.items():
                if meta.get("mtime_epoch") is not None and meta["mtime_epoch"] < newest_source_mtime:
                    stale_inputs.append(name)

        self.repomix_freshness = {
            "critical_dirs": {
                label: datetime.fromtimestamp(mtime).isoformat()
                for label, mtime in critical_mtimes.items()
            },
            "stale_inputs": sorted(stale_inputs),
        }

        if stale_inputs:
            stale_list = ", ".join(sorted(stale_inputs))
            logger.warning(
                "Repomix inputs appear older than critical source directories: %s",
                stale_list,
            )
    
    def get_total_token_estimate(self) -> int:
        """Estimate total tokens from loaded files."""
        total_chars = sum(self.file_sizes.values())
        return int(total_chars / 4)


# =============================================================================
# RALPH WIGGUM AUDIT PROMPTS
# =============================================================================

SYSTEM_PROMPT = """You are an expert ML systems engineer performing a comprehensive audit of a dataset infrastructure against its corresponding ML pipeline implementations.

Your task is to cross-reference the dataset scaffold code against the actual ML model implementations and identify:
1. Interface mismatches (data formats, tensor shapes, sample rates, etc.)
2. Missing functionality required by the ML phases
3. Incorrect configurations or parameters
4. Schema/contract misalignments

Be thorough, precise, and provide actionable fixes with complete code when needed."""

# =============================================================================
# AGENT PROMPTS (SUB-PROMPTS)
# =============================================================================

PROMPT_DIRS = [PROJECT_ROOT / "prompts"]
PLUGIN_PROMPT_DIRS = os.environ.get("PLUGIN_PROMPT_DIRS", "")
if PLUGIN_PROMPT_DIRS:
    for raw_path in PLUGIN_PROMPT_DIRS.split(os.pathsep):
        if raw_path.strip():
            PROMPT_DIRS.append(Path(raw_path.strip()))


def _load_prompt_files(directories: List[Path]) -> Dict[str, str]:
    prompts: Dict[str, str] = {}
    for directory in directories:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".txt", ".md"}:
                continue
            try:
                prompts[f"{directory.name}/{path.name}"] = path.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:
                logger.warning(f"Failed to read prompt file {path}: {exc}")
    return prompts


def _build_prompt_bundle() -> str:
    prompt_files = _load_prompt_files(PROMPT_DIRS)
    if not prompt_files:
        return ""
    sections = []
    for name, content in prompt_files.items():
        if not content.strip():
            continue
        sections.append(f"[Prompt: {name}]\n{content.strip()}")
    return "\n\n".join(sections)


PLUGIN_PROMPT_BUNDLE = _build_prompt_bundle()

AGENT_SYSTEM_PROMPTS = {
    "contracts_agent": (
        SYSTEM_PROMPT
        + "\n\nYou are the Contracts Agent. Extract exact interface contracts with strict shapes, sample rates, and types."
    ),
    "audit_agent": (
        SYSTEM_PROMPT
        + "\n\nYou are the Audit Agent. Identify mismatches and risks with clear severity and fixes."
    ),
    "fixes_agent": (
        SYSTEM_PROMPT
        + "\n\nYou are the Fixes Agent. Produce complete, runnable replacement files with no truncation."
    ),
}

if PLUGIN_PROMPT_BUNDLE:
    for key, prompt_text in AGENT_SYSTEM_PROMPTS.items():
        AGENT_SYSTEM_PROMPTS[key] = (
            prompt_text
            + "\n\n# Plugin Prompts (Reference)\n"
            + PLUGIN_PROMPT_BUNDLE
        )

# =============================================================================
# SECOND-PASS CONTEXT (prior audit + known issues)
# =============================================================================

PREVIOUS_AUDIT_REPORT = "/Users/cameronbrooks/Server/AI-STEM-Separator-Mad-Scientist-Edition/outputs/dataset_audit_report.md"
PREVIOUS_AUDIT_REPORT_TXT = "/Users/cameronbrooks/Server/AI-STEM-Separator-Mad-Scientist-Edition/outputs/dataset_audit_report.txt"
AUDIT_FIXES_DIR = "/Users/cameronbrooks/Server/AI-STEM-Separator-Mad-Scientist-Edition/outputs/audit_fixes"

SECOND_PASS_CONTEXT = """This is a THIRD PASS audit. Prior audits were run and generated reports and fixes.

Prior audit report:
- {previous_audit_report}
- {previous_audit_report_txt}

Generated fixes (not applied):
- {audit_fixes_dir}/src/latent_processor.py
- {audit_fixes_dir}/src/degradation.py
- {audit_fixes_dir}/src/audio_dataset.py

Known issues with those generated fixes (do NOT repeat):
1) outputs/audit_fixes/src/latent_processor.py starts and ends with Markdown code fences (```python ... ```), making it invalid Python.
2) outputs/audit_fixes/src/degradation.py is truncated (only 37 lines, missing methods and the pipeline).
3) outputs/audit_fixes/src/audio_dataset.py is truncated mid-class (PairedAudioDataset never completes).
4) outputs/audit_fixes/src/latent_processor.py still lacks local VAE backend integration (ml-ops phase-2).

In this third pass, you must produce complete, valid Python files without Markdown fences or truncation.
"""


RALPH_PASS_1A_PROMPT = """# PASS 1A: Extract Interface Contracts (Phases 1-4)

{second_pass_context}

You are analyzing the ML-OPS phase implementations to extract their data interface contracts.

## Design Specifications (Canonical Reference)

{design_specs}

## Phase 1: Separator (QSCNet/SCNet)

{phase1_content}

## Phase 2: Compressor (VAE Encoder - DAC Style)

{phase2_content}

## Phase 3: Guide (LiLAC ControlNet)

{phase3_content}

## Phase 4: Generator (DiT with Flow Matching)

{phase4_content}

## Original Specifications (Parts 1-4)

### Part 1 Spec:
{spec1_content}

### Part 2 Spec:
{spec2_content}

### Part 3 Spec:
{spec3_content}

### Part 4 Spec:
{spec4_content}

---

## YOUR TASK

Extract the **data interface contracts** from phases 1-4. For each phase, document:

1. **Input Requirements**
   - Expected tensor shapes
   - Data types (float32, complex64, etc.)
   - Sample rates, channels, durations
   - File formats if applicable

2. **Output Specifications**
   - Output tensor shapes
   - Data types
   - Any metadata produced

3. **Configuration Requirements**
   - Required config fields
   - Default values
   - Validation constraints

4. **Dependencies Between Phases**
   - What each phase needs from previous phases
   - Data flow requirements

Format your response as a structured JSON object with keys: phase1, phase2, phase3, phase4.

Be PRECISE about tensor dimensions, sample rates, and compression ratios. The dataset infrastructure must match these exactly."""

RALPH_PASS_1B_PROMPT = """# PASS 1B: Extract Interface Contracts (Phase 5 + Synthesis)

{second_pass_context}

You are completing the interface contract extraction for phase 5.

## Design Specifications (Canonical Reference)

{design_specs}

## Previously Extracted Contracts (Phases 1-4)

{pass1a_contracts}

## Phase 5: Synthesizer (VAE Decoder - HiFi-GAN Style)

{phase5_content}

## Part 5 Spec:
{spec5_content}

---

## YOUR TASK

1. Extract the interface contract for Phase 5 (same format as phases 1-4)
2. Synthesize a complete contracts document combining all 5 phases
3. Verify cross-phase compatibility

Output a COMPLETE JSON object with all 5 phases (phase1, phase2, phase3, phase4, phase5).
Include the previously extracted contracts and add phase5."""


RALPH_PASS_2_PROMPT = """# PASS 2: Audit Dataset Scaffold Against Phase Contracts

{second_pass_context}

You have extracted the interface contracts from all 5 ML phases. Now audit the dataset scaffold.

## Extracted Interface Contracts (All 5 Phases)

{pass1_contracts}

## Post-Pass1 Contract Compatibility Checks

{pass1_validation}

## Design Specifications (Canonical Reference)

{design_specs}

## Current Dataset Scaffold Implementation

{dataset_content}

---

## YOUR TASK

Perform a detailed audit of the dataset scaffold against the phase interface contracts.

For each issue found, categorize as:
- **CRITICAL**: Will cause runtime failures or incorrect training
- **HIGH**: Significant mismatch that affects quality or compatibility
- **MEDIUM**: Suboptimal but functional
- **LOW**: Minor improvements or code quality

Check specifically for:

### 1. Audio Loading & Processing (`src/audio_dataset.py`, `src/webdataset_loader.py`)
- Sample rate handling (must be 44100 Hz)
- Channel handling (stereo)
- Duration/chunking compatibility with phase requirements
- Resampling correctness

### 2. Latent Processing (`src/latent_processor.py`)
- Compression ratio (must be 2048x)
- Latent channels (must be 64)
- DAC/Stable Audio VAE compatibility
- Placeholder vs real implementation status

### 3. Degradation Pipeline (`src/degradation.py`)
- Degradation types needed for training each phase
- Parameter ranges appropriate for audio restoration
- Config schema compatibility
- Missing "mad scientist" degradations for stem artifacts

### 4. Manifest & Storage (`src/manifest.py`, `scripts/create_shards.py`)
- Manifest schema compatibility with phase data loaders
- WebDataset shard format correctness
- Pairing logic for clean/degraded data

### 5. Configuration (`configs/`)
- Parameter alignment with design specs
- Missing required fields
- Incorrect default values

Output a structured audit report with:
1. Summary statistics (counts by severity)
2. Detailed findings (grouped by severity, then by file)
3. Each finding should include: file, line(s), issue, impact, recommended fix"""


RALPH_PASS_3_PROMPT = """# PASS 3: Generate Fixes and Replacement Files

{second_pass_context}

You have completed the audit. Now generate the fixes.

## Audit Findings from Pass 2

{pass2_audit}

## Design Specifications (Canonical Reference)

{design_specs}

## Current Dataset Scaffold

{dataset_content}

---

## YOUR TASK

Generate a comprehensive fix report with complete replacement files.

### Output Format

1. **EXECUTIVE SUMMARY** (2-3 paragraphs)
   - Overall assessment of dataset scaffold quality
   - Key issues that must be fixed before training
   - Recommendation (ready to use / needs fixes / needs major rework)

2. **AUDIT SUMMARY TABLE**
   | Severity | Count | Key Issues |
   |----------|-------|------------|
   | CRITICAL | X | ... |
   | HIGH | X | ... |
   | MEDIUM | X | ... |
   | LOW | X | ... |

3. **DETAILED FINDINGS**
   For each finding:
   - **ID**: AUDIT-XXX
   - **Severity**: CRITICAL/HIGH/MEDIUM/LOW
   - **File**: path/to/file.py
   - **Issue**: Description
   - **Impact**: What breaks if not fixed
   - **Fix**: How to fix it

4. **COMPLETE REPLACEMENT FILES**
   For any file that needs changes, provide the COMPLETE fixed version.
   Use this delimiter format:
   
   ```
   # ============================================================
   # FILE: path/to/file.py
   # ============================================================
   [complete file contents - no truncation, no TODO, no ...]
   ```

IMPORTANT:
- Every replacement file must be COMPLETE and RUNNABLE
- No placeholders, no "...", no "# TODO: implement"
- Include all imports, all functions, all classes
- Code must be compatible with Python 3.11 and Linux
- If a file is fine, don't include it in replacements

Focus on fixes for:
1. The most critical interface mismatches
2. The latent processor (DAC integration)
3. The degradation pipeline (config schema + missing methods)
4. Any manifest/schema issues

Generate the complete audit report now."""


# =============================================================================
# AUDIT ENGINE
# =============================================================================

class DatasetAuditEngine:
    """
    Multi-pass audit engine using Ralph Wiggum methodology.
    
    Pass 1: Extract interface contracts from ML phases
    Pass 2: Audit dataset scaffold against contracts
    Pass 3: Generate fixes and replacement files
    """
    
    def __init__(self, client: GrokClient, loaded_files: Dict[str, str]):
        self.client = client
        self.files = loaded_files
        self.pass1_result: Optional[str] = None
        self.pass1_validation: Optional[str] = None
        self.pipeline_wiring_validation: Optional[str] = None
        self.pass2_result: Optional[str] = None
        self.pass3_result: Optional[str] = None
        self.total_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
        }
    
    def _format_design_specs(self) -> str:
        """Format design specs as readable text."""
        return json.dumps(DESIGN_SPECS, indent=2)

    def _extract_json_object(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract a JSON object from a response string."""
        if not response:
            return None
        start = response.find("{")
        end = response.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(response[start : end + 1])
        except json.JSONDecodeError:
            return None

    def _validate_contracts_schema(
        self,
        payload: Dict[str, Any],
        required_phases: Sequence[str],
    ) -> List[str]:
        """Validate contracts schema and return errors."""
        errors = []
        if not isinstance(payload, dict):
            return ["Top-level JSON must be an object."]

        top_level_keys = set(payload.keys())
        expected_keys = set(required_phases)
        if top_level_keys != expected_keys:
            errors.append(
                "Top-level keys must be exactly: "
                + ", ".join(sorted(expected_keys))
                + f". Got: {', '.join(sorted(top_level_keys)) or 'none'}."
            )

        required_fields = {
            "input_requirements",
            "output_specifications",
            "configuration_requirements",
            "dependencies_between_phases",
        }
        for phase in required_phases:
            phase_payload = payload.get(phase)
            if not isinstance(phase_payload, dict):
                errors.append(f"{phase} must be an object.")
                continue
            missing_fields = required_fields - set(phase_payload.keys())
            if missing_fields:
                errors.append(
                    f"{phase} missing required fields: {', '.join(sorted(missing_fields))}."
                )
        return errors

    def _require_valid_contracts_json(
        self,
        response: str,
        required_phases: Sequence[str],
        system_prompt: str,
        correction_context: str,
        max_attempts: int = 3,
    ) -> str:
        """Ensure contracts JSON is valid, re-prompting for corrections if needed."""
        current_response = response
        for attempt in range(max_attempts):
            payload = self._extract_json_object(current_response)
            if payload is None:
                errors = ["Response must be valid JSON."]
            else:
                errors = self._validate_contracts_schema(payload, required_phases)

            if not errors:
                return json.dumps(payload, indent=2)

            logger.warning(
                "Invalid contracts JSON (attempt %s/%s): %s",
                attempt + 1,
                max_attempts,
                "; ".join(errors),
            )

            correction_prompt = (
                "Your previous response did not match the required JSON schema.\n"
                f"Errors: {'; '.join(errors)}\n\n"
                "Return ONLY valid JSON with this exact schema:\n"
                "{\n"
                + ",\n".join(
                    f'  "{phase}": {{\n'
                    '    "input_requirements": {},\n'
                    '    "output_specifications": {},\n'
                    '    "configuration_requirements": {},\n'
                    '    "dependencies_between_phases": {}\n'
                    "  }"
                    for phase in required_phases
                )
                + "\n}\n\n"
                f"Context to correct:\n{correction_context}\n\n"
                "Previous response:\n"
                f"{current_response}"
            )

            current_response, usage = self.client.analyze(
                correction_prompt,
                system_prompt=system_prompt,
            )
            self._update_usage(usage)

        raise RuntimeError(
            "Failed to produce valid contracts JSON after "
            f"{max_attempts} attempts."
        )
    
    def run_pass1(self) -> str:
        """Pass 1: Extract interface contracts from phases (chunked to avoid token limit)."""
        logger.info("\n" + "=" * 70)
        logger.info("  PASS 1A: Extract Interface Contracts (Phases 1-4)")
        logger.info("=" * 70)
        
        prompt_1a = RALPH_PASS_1A_PROMPT.format(
            second_pass_context=SECOND_PASS_CONTEXT.format(
                previous_audit_report=PREVIOUS_AUDIT_REPORT,
                previous_audit_report_txt=PREVIOUS_AUDIT_REPORT_TXT,
                audit_fixes_dir=AUDIT_FIXES_DIR,
            ),
            design_specs=self._format_design_specs(),
            phase1_content=self.files.get("repomix_phase1", "Phase 1 content not available"),
            phase2_content=self.files.get("repomix_phase2", "Phase 2 content not available"),
            phase3_content=self.files.get("repomix_phase3", "Phase 3 content not available"),
            phase4_content=self.files.get("repomix_phase4", "Phase 4 content not available"),
            spec1_content=self.files.get("spec_part1", "Spec 1 not available"),
            spec2_content=self.files.get("spec_part2", "Spec 2 not available"),
            spec3_content=self.files.get("spec_part3", "Spec 3 not available"),
            spec4_content=self.files.get("spec_part4", "Spec 4 not available"),
        )
        
        response_1a, usage_1a = self.client.analyze(
            prompt_1a,
            system_prompt=AGENT_SYSTEM_PROMPTS["contracts_agent"]
        )
        self._update_usage(usage_1a)
        response_1a = self._require_valid_contracts_json(
            response_1a,
            required_phases=("phase1", "phase2", "phase3", "phase4"),
            system_prompt=AGENT_SYSTEM_PROMPTS["contracts_agent"],
            correction_context=prompt_1a,
        )
        logger.info("Pass 1A complete. Phases 1-4 contracts extracted.")

        logger.info("\n" + "=" * 70)
        logger.info("  PASS 1B: Extract Interface Contracts (Phase 5 + Synthesis)")
        logger.info("=" * 70)

        prompt_1b = RALPH_PASS_1B_PROMPT.format(
            second_pass_context=SECOND_PASS_CONTEXT.format(
                previous_audit_report=PREVIOUS_AUDIT_REPORT,
                previous_audit_report_txt=PREVIOUS_AUDIT_REPORT_TXT,
                audit_fixes_dir=AUDIT_FIXES_DIR,
            ),
            design_specs=self._format_design_specs(),
            pass1a_contracts=response_1a,
            phase5_content=self.files.get("repomix_phase5", "Phase 5 content not available"),
            spec5_content=self.files.get("spec_part5", "Spec 5 not available"),
        )

        response_1b, usage_1b = self.client.analyze(
            prompt_1b,
            system_prompt=AGENT_SYSTEM_PROMPTS["contracts_agent"]
        )
        self._update_usage(usage_1b)
        response_1b = self._require_valid_contracts_json(
            response_1b,
            required_phases=("phase1", "phase2", "phase3", "phase4", "phase5"),
            system_prompt=AGENT_SYSTEM_PROMPTS["contracts_agent"],
            correction_context=prompt_1b,
        )
        logger.info("Pass 1B complete. All contracts synthesized.")

        self.pass1_result = response_1b
        self.pass1_validation = self._validate_contract_compatibility(response_1b)
        self.pipeline_wiring_validation = self.validate_pipeline_wiring(response_1b)
        if self.pipeline_wiring_validation:
            self.pass1_validation = "\n\n".join(
                result
                for result in [self.pass1_validation, self.pipeline_wiring_validation]
                if result
            )
        return response_1b
    
    def run_pass2(self) -> str:
        """Pass 2: Audit dataset scaffold against contracts."""
        if not self.pass1_result:
            raise RuntimeError("Must run Pass 1 before Pass 2")
        
        logger.info("\n" + "=" * 70)
        logger.info("  PASS 2: Audit Dataset Scaffold - \"My cat's breath smells like cat food\"")
        logger.info("=" * 70)
        
        prompt = RALPH_PASS_2_PROMPT.format(
            second_pass_context=SECOND_PASS_CONTEXT.format(
                previous_audit_report=PREVIOUS_AUDIT_REPORT,
                previous_audit_report_txt=PREVIOUS_AUDIT_REPORT_TXT,
                audit_fixes_dir=AUDIT_FIXES_DIR,
            ),
            pass1_contracts=self.pass1_result,
            pass1_validation=self.pass1_validation or "No post-pass1 validation results available.",
            design_specs=self._format_design_specs(),
            dataset_content=self.files.get("repomix_dataset", "Dataset content not available"),
        )
        
        response, usage = self.client.analyze(
            prompt,
            system_prompt=AGENT_SYSTEM_PROMPTS["audit_agent"]
        )
        self._update_usage(usage)
        
        self.pass2_result = response
        logger.info(f"Pass 2 complete. Audit findings generated.")
        
        return response
    
    def run_pass3(self) -> str:
        """Pass 3: Generate fixes and replacement files."""
        if not self.pass2_result:
            raise RuntimeError("Must run Pass 2 before Pass 3")
        
        logger.info("\n" + "=" * 70)
        logger.info("  PASS 3: Generate Fixes - \"I'm a furniture!\"")
        logger.info("=" * 70)
        
        prompt = RALPH_PASS_3_PROMPT.format(
            second_pass_context=SECOND_PASS_CONTEXT.format(
                previous_audit_report=PREVIOUS_AUDIT_REPORT,
                previous_audit_report_txt=PREVIOUS_AUDIT_REPORT_TXT,
                audit_fixes_dir=AUDIT_FIXES_DIR,
            ),
            pass2_audit=self.pass2_result,
            design_specs=self._format_design_specs(),
            dataset_content=self.files.get("repomix_dataset", "Dataset content not available"),
        )
        
        response, usage = self.client.analyze(
            prompt,
            system_prompt=AGENT_SYSTEM_PROMPTS["fixes_agent"]
        )
        self._update_usage(usage)
        
        self.pass3_result = response
        logger.info(f"Pass 3 complete. Fixes generated.")
        
        return response
    
    def run_full_audit(self) -> str:
        """Run all three passes and return final report."""
        self.run_pass1()
        self.run_pass2()
        self.run_pass3()
        
        # Log total usage
        logger.info("\n" + "-" * 60)
        logger.info("  TOTAL API USAGE:")
        logger.info("-" * 60)
        logger.info(f"  Total input tokens:  {self.total_usage['input_tokens']:,}")
        logger.info(f"  Total output tokens: {self.total_usage['output_tokens']:,}")
        
        return self.pass3_result
    
    def _update_usage(self, usage: Dict):
        """Accumulate usage statistics."""
        self.total_usage["input_tokens"] += usage.get("input_tokens", 0)
        self.total_usage["output_tokens"] += usage.get("output_tokens", 0)

    def _validate_contract_compatibility(self, contracts_text: str) -> str:
        """Validate cross-phase contract compatibility from Pass 1 JSON output."""
        contracts = self._parse_contracts_json(contracts_text)
        issues: List[Tuple[str, str]] = []

        if not contracts:
            issues.append((
                "CRITICAL",
                "Unable to parse Pass 1 contracts JSON. Wiring validation could not be performed."
            ))
            return self._format_validation_report(issues)

        phase2 = contracts.get("phase2", {})
        phase3 = contracts.get("phase3", {})
        phase4 = contracts.get("phase4", {})
        phase5 = contracts.get("phase5", {})

        phase2_latent_channels = self._find_numeric_by_keys(
            phase2,
            [
                "latentchannels",
                "latent_channel",
                "latent_channels",
                "latentdim",
                "latentdims",
                "latentschannels",
                "latentschannel",
            ],
        )
        phase3_input_channels = self._find_numeric_by_keys(
            phase3,
            [
                "inputchannels",
                "input_channel",
                "input_channels",
                "inchannels",
            ],
        )
        phase3_guide_channels = self._find_numeric_by_keys(
            phase3,
            [
                "guidechannels",
                "guide_channels",
                "conditioningchannels",
                "controlchannels",
                "control_channels",
            ],
        )
        phase4_guide_inputs = self._find_numeric_by_keys(
            phase4,
            [
                "guidechannels",
                "guide_channels",
                "conditioningchannels",
                "controlchannels",
                "control_channels",
                "guideinput",
                "guide_input",
            ],
        )
        phase4_output_latents = self._find_numeric_by_keys(
            phase4,
            [
                "latentchannels",
                "latent_channel",
                "latent_channels",
                "outputlatents",
                "latentschannels",
                "latentdim",
            ],
        )
        phase5_input_latents = self._find_numeric_by_keys(
            phase5,
            [
                "latentchannels",
                "latent_channel",
                "latent_channels",
                "inputlatents",
                "input_latents",
                "latentdim",
            ],
        )

        if phase3_input_channels is None:
            issues.append((
                "CRITICAL",
                "Phase 3 input channel count is missing; cannot validate Phase2 → Phase3 wiring."
            ))
        elif phase3_input_channels != 64:
            issues.append((
                "CRITICAL",
                f"Phase 3 input_channels expected 64 but found {phase3_input_channels}."
            ))

        if phase2_latent_channels is None:
            issues.append((
                "CRITICAL",
                "Phase 2 latent channel count is missing; cannot validate Phase2 → Phase3 wiring."
            ))
        elif phase3_input_channels is not None and phase2_latent_channels != phase3_input_channels:
            issues.append((
                "CRITICAL",
                "Phase 2 latent channels do not match Phase 3 input channels "
                f"({phase2_latent_channels} vs {phase3_input_channels})."
            ))

        if phase3_guide_channels is None or phase4_guide_inputs is None:
            issues.append((
                "CRITICAL",
                "Missing guide channel counts for Phase3 → Phase4 wiring validation."
            ))
        elif phase3_guide_channels != phase4_guide_inputs:
            issues.append((
                "CRITICAL",
                "Phase 3 guide output channels do not match Phase 4 guide input channels "
                f"({phase3_guide_channels} vs {phase4_guide_inputs})."
            ))

        if phase4_output_latents is None or phase5_input_latents is None:
            issues.append((
                "CRITICAL",
                "Missing latent channel counts for Phase4 → Phase5 wiring validation."
            ))
        elif phase4_output_latents != phase5_input_latents:
            issues.append((
                "CRITICAL",
                "Phase 4 output latents do not match Phase 5 input latents "
                f"({phase4_output_latents} vs {phase5_input_latents})."
            ))

        report = self._format_validation_report(issues)
        for severity, message in issues:
            if severity == "CRITICAL":
                logger.error(f"[Contract Validation] {message}")
            else:
                logger.warning(f"[Contract Validation] {message}")
        if not issues:
            logger.info("Post-pass1 contract compatibility validation passed with no issues.")
        return report

    def validate_pipeline_wiring(self, contracts_text: str) -> str:
        """Validate known pipeline wiring contracts and fail fast on incompatibility."""
        contracts = self._parse_contracts_json(contracts_text)
        issues: List[Tuple[str, str]] = []

        if not contracts:
            issues.append((
                "CRITICAL",
                "Unable to parse Pass 1 contracts JSON. Pipeline wiring validation could not be performed."
            ))
            report = self._format_validation_report(issues)
            raise RuntimeError(report)

        phase1 = contracts.get("phase1", {})
        phase2 = contracts.get("phase2", {})
        phase3 = contracts.get("phase3", {})
        phase4 = contracts.get("phase4", {})
        phase5 = contracts.get("phase5", {})

        phase1_output = phase1.get("output_specifications", {})
        phase2_input = phase2.get("input_requirements", {})
        phase2_output = phase2.get("output_specifications", {})
        phase3_input = phase3.get("input_requirements", {})
        phase3_output = phase3.get("output_specifications", {})
        phase4_input = phase4.get("input_requirements", {})
        phase4_output = phase4.get("output_specifications", {})
        phase5_input = phase5.get("input_requirements", {})

        phase1_channels = self._find_numeric_by_keys(
            phase1_output,
            ["channels", "channel", "stemchannels", "stereo"],
        )
        phase2_input_channels = self._find_numeric_by_keys(
            phase2_input,
            ["channels", "channel", "inputchannels", "input_channel", "input_channels"],
        )
        phase1_rate = self._find_numeric_by_keys(
            phase1_output,
            ["samplerate", "sample_rate", "sampleratehz", "audiohz", "audio_rate"],
        )
        phase2_rate = self._find_numeric_by_keys(
            phase2_input,
            ["samplerate", "sample_rate", "sampleratehz", "audiohz", "audio_rate"],
        )

        if phase1_channels is None or phase2_input_channels is None:
            issues.append((
                "CRITICAL",
                "Phase1 → Phase2 wiring missing explicit channel counts."
            ))
        elif phase1_channels != 2 or phase2_input_channels != 2:
            issues.append((
                "CRITICAL",
                "Phase1 → Phase2 requires stereo [B,2,T] but found "
                f"Phase1={phase1_channels}, Phase2={phase2_input_channels}."
            ))

        detected_phase1_rate = self._detect_sample_rate(phase1_output) or phase1_rate
        detected_phase2_rate = self._detect_sample_rate(phase2_input) or phase2_rate
        if detected_phase1_rate is None or detected_phase2_rate is None:
            issues.append((
                "CRITICAL",
                "Phase1 → Phase2 wiring missing sample rate (expected 44.1kHz)."
            ))
        elif detected_phase1_rate != 44100 or detected_phase2_rate != 44100:
            issues.append((
                "CRITICAL",
                "Phase1 → Phase2 requires 44.1kHz but found "
                f"Phase1={detected_phase1_rate}, Phase2={detected_phase2_rate}."
            ))

        if not self._contains_shape(phase1_output, channels=2):
            issues.append((
                "CRITICAL",
                "Phase1 output must declare shape [B,2,T] for Phase2 input compatibility."
            ))
        if not self._contains_shape(phase2_input, channels=2):
            issues.append((
                "CRITICAL",
                "Phase2 input must accept [B,2,T] audio from Phase1 output."
            ))

        phase2_latent_channels = self._find_numeric_by_keys(
            phase2_output,
            ["latentchannels", "latent_channel", "latent_channels", "latentdim", "latentschannels"],
        )
        phase3_input_channels = self._find_numeric_by_keys(
            phase3_input,
            ["inputchannels", "input_channel", "input_channels", "inchannels", "latentchannels"],
        )

        if phase2_latent_channels is None or phase3_input_channels is None:
            issues.append((
                "CRITICAL",
                "Phase2 → Phase3 wiring missing latent channel counts (expected 64)."
            ))
        elif phase2_latent_channels != 64 or phase3_input_channels != 64:
            issues.append((
                "CRITICAL",
                "Phase2 → Phase3 requires latent shape [B,64,T//2048] but found "
                f"Phase2={phase2_latent_channels}, Phase3={phase3_input_channels}."
            ))

        if not self._contains_temporal_factor(phase2_output, divisor=2048):
            issues.append((
                "CRITICAL",
                "Phase2 output must declare temporal factor T//2048 for Phase3 input compatibility."
            ))
        if not self._contains_temporal_factor(phase3_input, divisor=2048):
            issues.append((
                "CRITICAL",
                "Phase3 input must accept temporal factor T//2048 from Phase2 latents."
            ))

        phase3_guide_channels = self._find_numeric_by_keys(
            phase3_output,
            ["guidechannels", "guide_channels", "conditioningchannels", "controlchannels", "control_channels"],
        )
        phase4_input_channels = self._find_numeric_by_keys(
            phase4_input,
            ["inputchannels", "input_channel", "input_channels", "inchannels", "latentchannels"],
        )
        if phase3_guide_channels is None or phase4_input_channels is None:
            issues.append((
                "CRITICAL",
                "Phase3 → Phase4 wiring missing guide/latent channel counts for concatenation."
            ))
        elif phase4_input_channels != 128 or phase3_guide_channels * 2 != phase4_input_channels:
            issues.append((
                "CRITICAL",
                "Phase3 guide must concatenate with noise to 128 channels for Phase4 input, "
                f"found guide={phase3_guide_channels}, phase4_input={phase4_input_channels}."
            ))

        if not self._contains_t5_embeddings(phase4_input):
            issues.append((
                "CRITICAL",
                "Phase4 input must include T5 text embeddings alongside concatenated latents."
            ))

        phase4_output_latents = self._find_numeric_by_keys(
            phase4_output,
            ["latentchannels", "latent_channel", "latent_channels", "outputlatents", "latentschannels", "latentdim"],
        )
        phase5_input_latents = self._find_numeric_by_keys(
            phase5_input,
            ["latentchannels", "latent_channel", "latent_channels", "inputlatents", "input_latents", "latentdim"],
        )

        if phase4_output_latents is None or phase5_input_latents is None:
            issues.append((
                "CRITICAL",
                "Phase4 → Phase5 wiring missing latent channel counts."
            ))
        elif phase4_output_latents != phase5_input_latents:
            issues.append((
                "CRITICAL",
                "Phase4 output latents do not match Phase5 input latents "
                f"({phase4_output_latents} vs {phase5_input_latents})."
            ))

        report = self._format_validation_report(issues)
        for severity, message in issues:
            if severity == "CRITICAL":
                logger.error(f"[Pipeline Wiring Validation] {message}")
            else:
                logger.warning(f"[Pipeline Wiring Validation] {message}")

        if any(sev == "CRITICAL" for sev, _ in issues):
            raise RuntimeError(report)
        if not issues:
            logger.info("Pipeline wiring validation passed with no issues.")
        return report

    def _format_validation_report(self, issues: List[Tuple[str, str]]) -> str:
        status = "FAIL" if any(sev == "CRITICAL" for sev, _ in issues) else "PASS"
        lines = [
            "Post-Pass1 Contract Compatibility Checks",
            f"Status: {status}",
        ]
        if not issues:
            lines.append("No compatibility issues detected across phases.")
            return "\n".join(lines)

        lines.append("Findings:")
        for severity, message in issues:
            lines.append(f"- {severity}: {message}")
        return "\n".join(lines)

    def _parse_contracts_json(self, contracts_text: str) -> Optional[Dict[str, Any]]:
        if not contracts_text:
            return None

        fenced_match = re.search(r"```(?:json)?\n(.*?)```", contracts_text, re.DOTALL)
        if fenced_match:
            try:
                return json.loads(fenced_match.group(1))
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(contracts_text)
        except json.JSONDecodeError:
            pass

        start = contracts_text.find("{")
        end = contracts_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        snippet = contracts_text[start:end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            return None

    def _find_numeric_by_keys(self, data: Any, key_candidates: List[str]) -> Optional[int]:
        if data is None:
            return None
        if isinstance(data, dict):
            for key, value in data.items():
                normalized_key = re.sub(r"[^a-z0-9]", "", str(key).lower())
                if any(candidate in normalized_key for candidate in key_candidates):
                    parsed = self._parse_numeric(value)
                    if parsed is not None:
                        return parsed
                nested = self._find_numeric_by_keys(value, key_candidates)
                if nested is not None:
                    return nested
        elif isinstance(data, list):
            for item in data:
                nested = self._find_numeric_by_keys(item, key_candidates)
                if nested is not None:
                    return nested
        return None

    def _parse_numeric(self, value: Any) -> Optional[int]:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            match = re.search(r"(\d+)", value)
            if match:
                return int(match.group(1))
        return None

    def _contains_shape(self, data: Any, channels: int) -> bool:
        text = self._normalize_text(data)
        if not text:
            return False
        pattern = rf"\[?\s*b\s*,\s*{channels}\s*,\s*t\s*\]?"
        return bool(re.search(pattern, text))

    def _contains_temporal_factor(self, data: Any, divisor: int) -> bool:
        text = self._normalize_text(data)
        if not text:
            return False
        pattern = rf"t\s*(//|/)\s*{divisor}"
        return bool(re.search(pattern, text))

    def _contains_t5_embeddings(self, data: Any) -> bool:
        text = self._normalize_text(data)
        if not text:
            return False
        return "t5" in text or "text embed" in text or "text embedding" in text

    def _detect_sample_rate(self, data: Any) -> Optional[int]:
        text = self._normalize_text(data)
        if not text:
            return None
        if "44.1khz" in text or "44.1 khz" in text or "44100" in text:
            return 44100
        return None

    def _normalize_text(self, data: Any) -> str:
        if data is None:
            return ""
        if isinstance(data, str):
            return data.lower()
        try:
            return json.dumps(data).lower()
        except (TypeError, ValueError):
            return str(data).lower()


# =============================================================================
# REPORT GENERATOR
# =============================================================================

class ReportGenerator:
    """Generate and save audit reports."""

    MANDATORY_SECTIONS = (
        "Executive Summary",
        "Audit Summary Table",
        "Detailed Findings",
        "Replacement Files",
    )
    
    def __init__(
        self,
        output_path: Path,
        repomix_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
        repomix_freshness: Optional[Dict[str, Any]] = None,
        scope: str = "dataset_infrastructure_audit",
    ):
        self.output_path = output_path
        self.repomix_metadata = repomix_metadata or {}
        self.repomix_freshness = repomix_freshness or {}
        self.scope = scope

    def _collect_inputs(self) -> List[Dict[str, Any]]:
        inputs: List[Dict[str, Any]] = []
        for name, meta in sorted(self.repomix_metadata.items()):
            inputs.append(
                {
                    "name": name,
                    "path": meta.get("path", ""),
                    "mtime": meta.get("mtime", ""),
                    "sha256": meta.get("sha256", ""),
                    "size_bytes": meta.get("size_bytes", 0),
                    "size_chars": meta.get("size_chars", 0),
                }
            )
        return inputs

    def _format_front_matter(self, generated_at: str) -> str:
        lines = ["---"]
        lines.append(f"generated_at: {generated_at}")
        lines.append(f"model: {MODEL_NAME}")
        lines.append(f"scope: {self.scope}")

        inputs = self._collect_inputs()
        if inputs:
            lines.append("inputs:")
            for meta in inputs:
                lines.append(f"  - name: {meta['name']}")
                lines.append(f"    path: {meta['path']}")
                lines.append(f"    mtime: {meta['mtime']}")
                lines.append(f"    sha256: {meta['sha256']}")
                lines.append(f"    size_bytes: {meta['size_bytes']}")
                lines.append(f"    size_chars: {meta['size_chars']}")
        else:
            lines.append("inputs: []")
        lines.append("tool_version: 4.0.0")

        if self.repomix_freshness:
            critical_dirs = self.repomix_freshness.get("critical_dirs", {})
            stale_inputs = self.repomix_freshness.get("stale_inputs", [])
            lines.append("repomix_freshness:")
            lines.append("  critical_dirs:")
            if critical_dirs:
                for label, mtime in sorted(critical_dirs.items()):
                    lines.append(f"    {label}: {mtime}")
            else:
                lines.append("    {}")
            lines.append("  stale_inputs:")
            if stale_inputs:
                for name in stale_inputs:
                    lines.append(f"    - {name}")
            else:
                lines.append("    - none")

        lines.append("---")
        return "\n".join(lines)

    def _missing_sections(self, report_body: str) -> List[str]:
        missing = []
        for section in self.MANDATORY_SECTIONS:
            pattern = rf"^#{1,6}\s*{re.escape(section)}\b"
            if not re.search(pattern, report_body, flags=re.IGNORECASE | re.MULTILINE):
                missing.append(section)
        return missing

    def _post_process_report(self, report_body: str, generated_at: str) -> str:
        front_matter = self._format_front_matter(generated_at)
        return f"{front_matter}\n\n{report_body}"
    
    def save_report(self, audit_result: str, pass1: str, pass2: str) -> Path:
        """Save the complete audit report with all passes."""
        generated_at = datetime.now().isoformat()
        front_matter = self._format_front_matter(generated_at)
        warnings, validation_failed = self._extract_and_save_files(audit_result)
        warning_section = self._format_warning_section(warnings, validation_failed)

        report = f"""# Dataset Infrastructure Audit Report

**Generated:** {generated_at}
**Tool Version:** 4.0.0
**Model:** {MODEL_NAME}

---

{audit_result}

---

# Appendix A: Interface Contracts (Pass 1 Output)

<details>
<summary>Click to expand Pass 1 output</summary>

{pass1}

</details>

---

# Appendix B: Detailed Audit Findings (Pass 2 Output)

<details>
<summary>Click to expand Pass 2 output</summary>

{pass2}

</details>
{warning_section}
---

*Report generated by AI Stem Separator Dataset Audit Tool v4.0*
"""
        report = None
        for attempt in range(2):
            report = self._post_process_report(report_body, generated_at)
            missing_sections = self._missing_sections(report)
            if not missing_sections:
                break
            if attempt == 0:
                logger.warning(
                    "Report missing required sections (%s); retrying post-processing.",
                    ", ".join(missing_sections),
                )
                continue
            raise ValueError(
                "Missing required sections in report: "
                + ", ".join(missing_sections)
            )
        
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(report or "")
        
        logger.info(f"Report saved to: {self.output_path}")
        
        return self.output_path

    def _format_warning_section(self, warnings: List[str], validation_failed: bool) -> str:
        if not warnings:
            return ""
        heading = "## Fix Extraction Validation Failure" if validation_failed else "## Fix Extraction Warnings"
        warning_lines = "\n".join(f"- {warning}" for warning in warnings)
        return f"\n\n---\n\n{heading}\n\n{warning_lines}\n"

    def _extract_and_save_files(self, report: str) -> Tuple[List[str], bool]:
        """Extract replacement files from report and save them."""
        warnings: List[str] = []
        validation_failed = False
        extracted_files: List[Tuple[str, str]] = []

        # Pattern to match file blocks
        file_pattern = r'#\s*={3,}\s*\n#\s*FILE:\s*(.+?)\s*\n#\s*={3,}\s*\n(.*?)(?=#\s*={3,}|```\s*$|$)'

        matches = re.findall(file_pattern, report, re.DOTALL)

        if not matches:
            # Try alternative pattern with code fences
            file_pattern = r'```[a-z]*\n#\s*={3,}\s*\n#\s*FILE:\s*(.+?)\s*\n#\s*={3,}\s*\n(.*?)```'
            matches = re.findall(file_pattern, report, re.DOTALL)

        if not matches:
            warnings.append("No replacement file blocks were found in the audit report.")
            return warnings, validation_failed

        for file_path, content in matches:
            file_path = file_path.strip()
            content = content.strip()
            content, fence_warning, fence_failed = self._strip_markdown_fences(content)
            if fence_warning:
                warnings.append(f"Extracted file '{file_path}': {fence_warning}")
            if fence_failed:
                validation_failed = True
                continue

            if file_path.endswith(".py") and not self._starts_with_shebang_or_docstring(content):
                warnings.append(
                    f"Rejected extracted file '{file_path}' due to missing shebang or module docstring."
                )
                validation_failed = True
                continue

            extracted_files.append((file_path, content))

        if validation_failed:
            warnings.append("Validation failed; no replacement files were written.")
            return warnings, validation_failed

        if not extracted_files:
            warnings.append("No valid replacement files were extracted from the audit report.")
            return warnings, validation_failed

        fixes_dir = self.output_path.parent / "audit_fixes"
        fixes_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"\nExtracting {len(extracted_files)} replacement files to {fixes_dir}")

        for file_path, content in extracted_files:
            # Normalize path
            if file_path.startswith('/'):
                file_path = file_path.lstrip('/')

            output_file = fixes_dir / file_path
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"  Saved: {output_file}")

        return warnings, validation_failed

    def _strip_markdown_fences(self, content: str) -> Tuple[str, Optional[str], bool]:
        """Remove surrounding markdown fences and detect truncation."""
        stripped = content.strip()
        if not stripped:
            return "", "Empty extracted content.", True

        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) < 2:
                return "", "Markdown fence provided without content.", True
            if not lines[-1].strip().startswith("```"):
                return "", "Markdown fence missing closing delimiter.", True
            stripped = "\n".join(lines[1:-1]).strip()

        # Detect embedded markdown fences only when they appear as standalone fence lines,
        # not when triple backticks are used inline within strings or comments.
        embedded_fence_index: Optional[int] = None
        lines = stripped.splitlines()
        for idx, line in enumerate(lines):
            if line.strip().startswith("```"):
                embedded_fence_index = idx
                break

        if embedded_fence_index is not None:
            truncated = "\n".join(lines[:embedded_fence_index]).rstrip()
            return truncated, "Embedded markdown fence detected; content truncated.", True

        return stripped, None, False

    def _starts_with_shebang_or_docstring(self, content: str) -> bool:
        """Validate that python files start with a shebang or module docstring."""
        stripped = content.lstrip()
        if not stripped:
            return False

        if stripped.startswith("#!"):
            first_line = stripped.splitlines()[0]
            return re.match(r"^#!.*\bpython(\d+(\.\d+)*)?\b", first_line) is not None

        return stripped.startswith('"""') or stripped.startswith("'''")


def save_interpass_outputs(output_dir: Path, pass1: str, pass2: str, pass3: str):
    """Save per-pass outputs for diffing and audit trail."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pass1_contracts.txt").write_text(pass1 or "")
    (output_dir / "pass2_audit.txt").write_text(pass2 or "")
    (output_dir / "pass3_fixes.txt").write_text(pass3 or "")


# =============================================================================
# CLI
# =============================================================================

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Audit dataset infrastructure against ML phase implementations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --output /path/to/report.md
  %(prog)s --pass1-only  # Only extract contracts
  %(prog)s --verbose

Environment Variables:
  XAI_API_KEY          Your xAI API key (required)
        """
    )
    
    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=DEFAULT_AUDIT_OUTPUT,
        help=f'Output path for audit report (default: {DEFAULT_AUDIT_OUTPUT})'
    )
    
    parser.add_argument(
        '--pass1-only',
        action='store_true',
        help='Only run Pass 1 (extract contracts)'
    )
    
    parser.add_argument(
        '--pass2-only',
        action='store_true',
        help='Only run Pass 1 and 2 (skip fix generation)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing output report'
    )

    parser.add_argument(
        '--manifest-report',
        type=Path,
        help='Path to a prior analysis report used as a rubric (markdown)'
    )

    parser.add_argument(
        '--manifest-report-txt',
        type=Path,
        help='Optional text version of the rubric report'
    )

    parser.add_argument(
        '--project-root',
        type=Path,
        help='Override the project root directory'
    )

    parser.add_argument(
        '--dataset-dir',
        type=Path,
        help='Override the dataset directory'
    )

    parser.add_argument(
        '--outputs-dir',
        type=Path,
        help='Override the outputs directory'
    )
    
    return parser.parse_args()


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    """Main entry point."""
    
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║     AI STEM SEPARATOR DATASET AUDIT TOOL v4.0                        ║
║     Cross-Reference & Validation Engine                              ║
║     Using Grok with 2M Token Context                                 ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    args = parse_arguments()
    global PREVIOUS_AUDIT_REPORT, PREVIOUS_AUDIT_REPORT_TXT
    global PROJECT_ROOT, DATASET_DIR, OUTPUTS_DIR, DEFAULT_AUDIT_OUTPUT
    global REPOMIX_PHASE_PATHS, REPOMIX_DATASET_PATH, PROMPT_DIRS

    if args.project_root:
        PROJECT_ROOT = args.project_root
    if args.dataset_dir:
        DATASET_DIR = args.dataset_dir
    elif args.project_root:
        DATASET_DIR = PROJECT_ROOT / "dataset"
    if args.outputs_dir:
        OUTPUTS_DIR = args.outputs_dir
    elif args.project_root:
        OUTPUTS_DIR = PROJECT_ROOT / "outputs"

    if args.project_root or args.outputs_dir:
        DEFAULT_AUDIT_OUTPUT = OUTPUTS_DIR / "third_pass" / "dataset_audit_report.md"
        if args.output == DEFAULT_AUDIT_OUTPUT:
            args.output = DEFAULT_AUDIT_OUTPUT

        REPOMIX_PHASE_PATHS = {
            "phase1": OUTPUTS_DIR / "repomix_phase1.md",
            "phase2": OUTPUTS_DIR / "repomix_phase2.md",
            "phase3": OUTPUTS_DIR / "repomix_phase3.md",
            "phase4": OUTPUTS_DIR / "repomix_phase4.md",
            "phase5": OUTPUTS_DIR / "repomix_phase5.md",
        }
        REPOMIX_DATASET_PATH = OUTPUTS_DIR / "repomix_dataset.md"

        PROMPT_DIRS = [PROJECT_ROOT / "prompts"]
        plugin_dirs = os.environ.get("PLUGIN_PROMPT_DIRS", "")
        if plugin_dirs:
            for raw_path in plugin_dirs.split(os.pathsep):
                if raw_path.strip():
                    PROMPT_DIRS.append(Path(raw_path.strip()))

    if args.manifest_report:
        PREVIOUS_AUDIT_REPORT = str(args.manifest_report)
    if args.manifest_report_txt:
        PREVIOUS_AUDIT_REPORT_TXT = str(args.manifest_report_txt)
    elif args.manifest_report and args.manifest_report.with_suffix(".txt").exists():
        PREVIOUS_AUDIT_REPORT_TXT = str(args.manifest_report.with_suffix(".txt"))
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        validated_dataset_dir = _validate_dataset_dir(DATASET_DIR)

        # Load all files
        loader = FileLoader()
        files = loader.load_all()
        
        # Check token estimate
        token_estimate = loader.get_total_token_estimate()
        if token_estimate > MAX_CONTEXT_TOKENS:
            logger.error(f"Content too large: ~{token_estimate:,} tokens exceeds {MAX_CONTEXT_TOKENS:,} limit")
            return 1
        
        # Initialize Grok client
        client = GrokClient()
        
        # Run audit
        engine = DatasetAuditEngine(client, files)
        
        if args.pass1_only:
            result = engine.run_pass1()
            print("\n" + "=" * 70)
            print("PASS 1 RESULT (Interface Contracts)")
            print("=" * 70)
            print(result)
        elif args.pass2_only:
            engine.run_pass1()
            result = engine.run_pass2()
            print("\n" + "=" * 70)
            print("PASS 2 RESULT (Audit Findings)")
            print("=" * 70)
            print(result)
        else:
            if args.output.exists() and not args.force:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                args.output = args.output.with_name(
                    f"{args.output.stem}_{timestamp}{args.output.suffix}"
                )
                logger.warning(f"Output exists; writing to {args.output}")
            result = engine.run_full_audit()
            
            # Save report
            reporter = ReportGenerator(args.output, validated_dataset_dir)
            reporter.save_report(
                result,
                engine.pass1_result,
                engine.pass2_result
            )
            save_interpass_outputs(
                args.output.parent,
                engine.pass1_result or "",
                engine.pass2_result or "",
                engine.pass3_result or ""
            )
        
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    ✅ AUDIT COMPLETE!                                ║
╚══════════════════════════════════════════════════════════════════════╝
        """)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ File Error: {e}")
        return 1
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        return 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        return 130
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {type(e).__name__}: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
