"""
Configuration management for PicoCloth-CLI.

Uses Pydantic Settings for type-safe, environment-aware configuration.
Config is stored in ~/.picocloth/config.yaml and merged with environment
variables and sensible defaults.

Citation: Microsoft Agent Framework 1.0 pluggable memory & checkpointing
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from picocloth_cli.core.constants import (
    CLI_CONFIG_PATH,
    CLI_LOGS_DIR,
    CLI_SESSIONS_DIR,
    CLI_CACHE_DIR,
    PICOCLOTH_DIR,
    SHARED_DIR,
    INTENT_CONFIDENCE_THRESHOLD,
    SPAWN_COMPLEXITY_THRESHOLD,
    MAX_SPAWN_DEPTH,
)
from picocloth_cli.core.exceptions import ConfigError


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "rich"  # "rich" | "json" | "plain"
    file_enabled: bool = True
    file_path: Path = Field(default_factory=lambda: CLI_LOGS_DIR / "picocloth-cli.log")
    max_bytes: int = 10_485_760  # 10 MiB
    backup_count: int = 5


class FleetConfig(BaseModel):
    """Fleet connection configuration."""

    shared_dir: Path = SHARED_DIR
    server_path: Path = PICOCLOTH_DIR / "mcp-fleet-server" / "server.py"
    transport: str = "stdio"  # "stdio" | "http"
    http_base_url: str = "http://127.0.0.1:18880"
    heartbeat_interval: int = 30
    connection_timeout: float = 10.0


class IntentConfig(BaseModel):
    """Intent engine configuration."""

    confidence_threshold: float = INTENT_CONFIDENCE_THRESHOLD
    complexity_threshold: float = SPAWN_COMPLEXITY_THRESHOLD
    max_spawn_depth: int = MAX_SPAWN_DEPTH
    rule_based_first: bool = True
    llm_fallback: bool = True
    fallback_model: str = "grok-4.1-fast"


class MemoryConfig(BaseModel):
    """Memory layer configuration."""

    lock_timeout: float = 5.0
    compaction_threshold_percent: int = 75
    max_facts_per_compaction: int = 8
    enable_digital_twin: bool = True


class UIConfig(BaseModel):
    """User interface configuration."""

    theme: str = "default"
    table_style: str = "cyan"
    progress_refresh_rate: float = 0.5
    markdown_max_width: int = 100
    show_citations: bool = True


class CLIConfig(BaseSettings):
    """Root configuration model for PicoCloth-CLI.

    Loaded from ~/.picocloth/config.yaml with environment variable overrides.
    Env vars are prefixed with PICOLOTH_ (e.g., PICOLOTH_FLEET__TRANSPORT).
    """

    model_config = SettingsConfigDict(
        env_prefix="PICOLOTH_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    picocloth_dir: Path = PICOCLOTH_DIR
    sessions_dir: Path = CLI_SESSIONS_DIR
    cache_dir: Path = CLI_CACHE_DIR

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    fleet: FleetConfig = Field(default_factory=FleetConfig)
    intent: IntentConfig = Field(default_factory=IntentConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    ui: UIConfig = Field(default_factory=UIConfig)

    @field_validator("picocloth_dir", mode="before")
    @classmethod
    def _resolve_path(cls, v: Any) -> Path:
        if isinstance(v, str):
            return Path(v).expanduser().resolve()
        return v

    @field_validator("logging", "fleet", "intent", "memory", "ui", mode="before")
    @classmethod
    def _dict_to_model(cls, v: Any, info: Any) -> Any:
        """Allow partial dicts to be merged with defaults."""
        if isinstance(v, dict):
            model_cls = {
                "logging": LoggingConfig,
                "fleet": FleetConfig,
                "intent": IntentConfig,
                "memory": MemoryConfig,
                "ui": UIConfig,
            }.get(info.field_name)
            if model_cls:
                # Start with defaults, then overlay provided keys
                defaults = model_cls().model_dump()
                defaults.update(v)
                return model_cls(**defaults)
        return v


# ---------------------------------------------------------------------------
# Singleton config instance
# ---------------------------------------------------------------------------

_CONFIG: CLIConfig | None = None


def load_config(config_path: Path | None = None) -> CLIConfig:
    """Load configuration from YAML file, creating defaults if missing.

    Returns a validated CLIConfig instance. Raises ConfigError on parse failure.
    """
    global _CONFIG
    if _CONFIG is not None and config_path is None:
        return _CONFIG

    path = config_path or CLI_CONFIG_PATH

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Load from file if it exists
    file_data: dict[str, Any] = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                file_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"Failed to parse config YAML: {exc}") from exc
        except OSError as exc:
            raise ConfigError(f"Failed to read config file: {exc}") from exc

    # Merge with environment variables (Pydantic Settings handles this)
    try:
        _CONFIG = CLIConfig(**file_data)
    except Exception as exc:
        raise ConfigError(f"Config validation failed: {exc}") from exc

    return _CONFIG


def save_config(config: CLIConfig, config_path: Path | None = None) -> None:
    """Save configuration to YAML file atomically.

    Uses write-to-temp-then-rename for crash safety.
    Citation: Claude Code file-lock pattern (Anthropic, Feb 2026)
    """
    path = config_path or CLI_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    # Exclude internal Pydantic fields and defaults to keep YAML clean
    data = config.model_dump(
        mode="json",
        exclude_unset=False,
        exclude_defaults=False,
    )

    temp_path = path.with_suffix(".yaml.tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        temp_path.replace(path)
    except OSError as exc:
        raise ConfigError(f"Failed to write config file: {exc}") from exc
    finally:
        if temp_path.exists():
            temp_path.unlink()


def get_config() -> CLIConfig:
    """Return the loaded config singleton, loading if necessary."""
    if _CONFIG is None:
        return load_config()
    return _CONFIG


def reload_config() -> CLIConfig:
    """Force reload of configuration from disk."""
    global _CONFIG
    _CONFIG = None
    return load_config()
