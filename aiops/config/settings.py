from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import BaseModel, Field

from .logs_config import LogsConfig
from .metrics_config import MetricsConfig
from .security_config import SecurityConfig


class Settings(BaseModel):
    """Root configuration model."""

    app_name: str = Field(default="aiops-agent")
    environment: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    data_dir: str = Field(default="data")
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    logs: LogsConfig = Field(default_factory=LogsConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("Config file root must be a mapping")
    return data


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _set_nested(data: Dict[str, Any], keys: list[str], value: Any) -> None:
    current = data
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    current[keys[-1]] = value


def _collect_env_overrides(prefix: str, delimiter: str = "__") -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        stripped = key[len(prefix):]
        if not stripped:
            continue
        parts = [part.lower() for part in stripped.split(delimiter) if part]
        if not parts:
            continue
        _set_nested(overrides, parts, value)
    return overrides


def load_settings(config_path: str | Path | None = None, env_prefix: str = "AIOPS_") -> Settings:
    path: Path | None = None
    if config_path:
        path = Path(config_path)
    else:
        env_path = os.getenv(f"{env_prefix}CONFIG_FILE")
        if env_path:
            path = Path(env_path)

    file_data: Dict[str, Any] = {}
    if path:
        file_data = _load_yaml(path)

    env_data = _collect_env_overrides(env_prefix)
    merged = _deep_merge(file_data, env_data)
    return Settings.model_validate(merged)


class ConfigManager:
    """Simple config manager with manual reload capability."""

    def __init__(self, config_path: str | Path | None = None, env_prefix: str = "AIOPS_") -> None:
        self._config_path = Path(config_path) if config_path else None
        self._env_prefix = env_prefix
        self._last_mtime: float | None = None
        self.settings = load_settings(self._config_path, env_prefix=self._env_prefix)
        self._update_mtime()

    @property
    def config_path(self) -> Path | None:
        return self._config_path

    def _update_mtime(self) -> None:
        if not self._config_path or not self._config_path.exists():
            self._last_mtime = None
            return
        self._last_mtime = self._config_path.stat().st_mtime

    def reload(self) -> Settings:
        self.settings = load_settings(self._config_path, env_prefix=self._env_prefix)
        self._update_mtime()
        return self.settings

    def check_reload(self) -> bool:
        if not self._config_path or not self._config_path.exists():
            return False
        mtime = self._config_path.stat().st_mtime
        if self._last_mtime is None or mtime > self._last_mtime:
            self.reload()
            return True
        return False

