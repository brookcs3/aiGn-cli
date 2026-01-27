import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Union

try:
    from rich.console import Console
    console = Console()
except ImportError:
    class Console:
        def print(self, *args, **kwargs):
            print(*args)
        def status(self, *args, **kwargs):
            class StatusContext:
                def __enter__(self): return self
                def __exit__(self, *args): pass
            return StatusContext()
    console = Console()

# Constants
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLI_ROOT = PROJECT_ROOT / "src" / "cli"
DEEP_CLI_ROOT = CLI_ROOT / "Deep-CLI"
OUTPUTS_ROOT = PROJECT_ROOT / "src" / "outputs"

# Persona Resources
PHRASES_FILE = CLI_ROOT / "dylan_phrases.csv"
ADAPTER_CHECKPOINT = CLI_ROOT / "madsci_dylan_adapter" / "checkpoint-96"

# Default Configuration
DEFAULT_CONFIG = {
    "timeout": 300,
    "log_level": "INFO",
    "analysis_output_dir": str(OUTPUTS_ROOT / "analysis"),
    "snapshot_output_dir": str(OUTPUTS_ROOT / "snapshots"),
    "pipeline_output_dir": str(OUTPUTS_ROOT / "pipeline"),
    "llm": {
        "backend": "xai",  # xai, anthropic, openai
        "model": "grok-beta",
        "max_tokens": 4096,
        "temperature": 0.7
    }
}

# Global Objects
console = Console()

def setup_logging(level: str = "INFO"):
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    return logging.getLogger("madsci")

logger = setup_logging(DEFAULT_CONFIG["log_level"])

def ensure_dir(path: Union[str, Path]):
    """Ensure a directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)

def load_config(config_path: Union[str, Path] = None) -> Dict[str, Any]:
    """Load configuration from file or return defaults."""
    # TODO: Implement JSON/YAML config loading
    # For now, return defaults
    return DEFAULT_CONFIG.copy()
