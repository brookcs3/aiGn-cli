import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
try:
    from .config import CLI_ROOT, logger, ensure_dir
except ImportError:
    from config import CLI_ROOT, logger, ensure_dir

STATE_FILE = CLI_ROOT / ".madsci_state.json"

class StateManager:
    """Manages persistent state for the CLI."""
    
    def __init__(self, state_path: Path = STATE_FILE):
        self.state_path = state_path
        self._state: Dict[str, Any] = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load state from JSON file."""
        if not self.state_path.exists():
            return {"created_at": time.time(), "sessions": {}}
        try:
            with open(self.state_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return {"created_at": time.time(), "error": str(e)}

    def save(self):
        """Save current state to JSON file."""
        ensure_dir(self.state_path.parent)
        try:
            with open(self.state_path, "w") as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the state."""
        return self._state.get(key, default)

    def set(self, key: str, value: Any):
        """Set a value in the state and save."""
        self._state[key] = value
        self.save()

    def update_section(self, section: str, data: Dict[str, Any]):
        """Update a specific section (dict) of the state."""
        if section not in self._state:
            self._state[section] = {}
        self._state[section].update(data)
        self.save()

# Global State Instance
state_manager = StateManager()
