"""Configuration management with multi-layer priority."""

import os
from pathlib import Path
from typing import Any, Optional

# Try to import yaml, but provide fallback
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

DEFAULT_CONFIG: dict[str, Any] = {
    "obsidian": {
        "vault_dir": "",
        "article_dir": "01-文章",
    },
    "sources": {
        "douyin": {
            "api_url": "",
            "timeout": 600,
        },
        "paper": {
            "max_size_mb": 50,
        },
    },
    "templates": {
        "custom_dir": None,
    },
    "network": {
        "proxy": None,
        "timeout": 30,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override dict into base dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(cli_overrides: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Load configuration with priority: CLI args > env vars > config file > defaults."""
    config = DEFAULT_CONFIG.copy()

    # Layer 1: Config file
    config_path = Path.home() / ".obsidian-capture" / "config.yaml"
    if config_path.exists() and HAS_YAML:
        with open(config_path, "r", encoding="utf-8") as f:
            file_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, file_config)

    # Layer 2: Environment variables
    env_map = {
        "OBSIDIAN_CAPTURE_VAULT_DIR": ("obsidian", "vault_dir"),
        "OBSIDIAN_CAPTURE_ARTICLE_DIR": ("obsidian", "article_dir"),
        "OBSIDIAN_CAPTURE_DOUYIN_API": ("sources", "douyin", "api_url"),
        "OBSIDIAN_CAPTURE_DOUYIN_TIMEOUT": ("sources", "douyin", "timeout"),
        "OBSIDIAN_CAPTURE_PROXY": ("network", "proxy"),
        "OBSIDIAN_CAPTURE_TIMEOUT": ("network", "timeout"),
    }

    for env_var, path in env_map.items():
        value = os.environ.get(env_var)
        if value is not None:
            # Handle numeric values
            if path[-1] in ("timeout", "max_size_mb"):
                try:
                    value = int(value)
                except ValueError:
                    continue
            # Navigate to the target dict and set value
            target = config
            for key in path[:-1]:
                target = target.setdefault(key, {})
            target[path[-1]] = value

    # Layer 3: CLI overrides (highest priority)
    if cli_overrides:
        config = _deep_merge(config, cli_overrides)

    return config


def ensure_config_dir() -> Path:
    """Ensure config directory exists, return path."""
    config_dir = Path.home() / ".obsidian-capture"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def create_default_config() -> str:
    """Create a default config file if it doesn't exist. Returns path."""
    config_dir = ensure_config_dir()
    config_path = config_dir / "config.yaml"

    if not config_path.exists():
        example = """# obsidian-capture configuration
obsidian:
  vault_dir: "D:\\\\WorkBuddy\\\\Claw\\\\Obsidian\\\\Obsidian"  # Replace with your Obsidian vault path
  article_dir: "01-文章"  # Relative to vault_dir

sources:
  douyin:
    api_url: ""  # Set your local Douyin API, e.g. "http://localhost:5050"
    timeout: 600  # Seconds, max wait for Whisper transcription
  paper:
    max_size_mb: 50  # Skip PDFs larger than this

templates:
  custom_dir: null  # Override default templates, e.g. "~/my-templates"

network:
  proxy: null  # e.g. "http://127.0.0.1:7890"
  timeout: 30  # Seconds for HTTP requests
"""
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(example)

    return str(config_path)


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate required config fields. Returns list of error messages."""
    errors = []

    vault_dir = config.get("obsidian", {}).get("vault_dir", "")
    if not vault_dir:
        errors.append("obsidian.vault_dir 未配置。请设置 Obsidian 库路径。")

    if vault_dir and not Path(vault_dir).exists():
        errors.append(f"Obsidian 库路径不存在: {vault_dir}")

    return errors
