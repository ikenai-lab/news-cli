import os
import json
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class Config:
    default_model: str = "llama3.2:3b"
    default_limit: int = 5

    @staticmethod
    def _get_config_path() -> Path:
        """Returns path to ~/.config/news-cli/config.json"""
        config_dir = Path.home() / ".config" / "news-cli"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.json"

    @classmethod
    def load(cls) -> "Config":
        """Loads config from file or returns defaults."""
        path = cls._get_config_path()
        if not path.exists():
            return cls()
        
        try:
            with open(path, "r") as f:
                data = json.load(f)
                # Filter unknown keys to allow adding fields later
                known_keys = cls().__dict__.keys()
                filtered_data = {k: v for k, v in data.items() if k in known_keys}
                return cls(**filtered_data)
        except Exception:
            return cls() # Fallback to defaults on error

    def save(self):
        """Saves current config to file."""
        path = self._get_config_path()
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=4)
            
    def set(self, key: str, value):
        """Updates a config value and persists it."""
        if hasattr(self, key):
             # Type conversion if needed
             if key == "default_limit":
                 value = int(value)
             setattr(self, key, value)
             self.save()
        else:
             raise KeyError(f"Unknown config key: {key}")

# Singleton instance
config = Config.load()
