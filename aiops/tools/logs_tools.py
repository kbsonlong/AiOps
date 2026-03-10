from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from aiops.config.settings import load_settings


def _get_default_vl_url() -> str:
    return load_settings().logs.victorialogs_base_url


def _get_default_otel_url() -> str:
    return load_settings().logs.otel_logs_query_url


def _candidate_log_files(log_type: str) -> List[Path]:
    if Path(log_type).exists():
        return [Path(log_type)]

    candidates: list[Path] = []
    if log_type in ("syslog", "system"):
        candidates = [
            Path("/var/log/system.log"),
            Path("/var/log/syslog"),
            Path("/var/log/messages"),
        ]
    elif log_type in ("auth", "security"):
        candidates = [
            Path("/var/log/auth.log"),
            Path("/var/log/secure"),
        ]
    elif log_type in ("all", "default"):
        candidates = [
            Path("/var/log/system.log"),
            Path("/var/log/syslog"),
            Path("/var/log/messages"),
            Path("/var/log/auth.log"),
            Path("/var/log/secure"),
        ]
    return [path for path in candidates if path.exists()]


def _read_tail(path: Path, lines: int) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    chunks = content.splitlines()[-lines:]
    return "\n".join(chunks)


def collect_system_logs(
    log_type: str = "syslog",
    lines: int = 100,
    base_url: str | None = None,
    query: str | None = None,
    timeout: float = 5.0,
) -> str:
    """Collect system logs from VictoriaLogs or local files."""
    if base_url:
        response = query_victorialogs(query or "error", base_url=base_url, limit=lines, timeout=timeout)
        return json.dumps(response, ensure_ascii=True)

    files = _candidate_log_files(log_type)
    if not files:
        return f"No log files found for log_type={log_type}"
    collected = []
    for path in files:
        tail = _read_tail(path, lines)
        if tail:
            collected.append(f"== {path} ==\n{tail}")
    return "\n\n".join(collected) if collected else f"No readable log content for log_type={log_type}"


def analyze_log_patterns(log_text: str) -> Dict[str, int]:
    """Analyze log patterns by counting severity keywords."""
    patterns = {
        "error": re.compile(r"\b(error|failed|fatal|exception)\b", re.IGNORECASE),
        "warn": re.compile(r"\b(warn|warning)\b", re.IGNORECASE),
        "info": re.compile(r"\b(info)\b", re.IGNORECASE),
    }
    counts = {key: 0 for key in patterns}
    for line in log_text.splitlines():
        for key, pattern in patterns.items():
            if pattern.search(line):
                counts[key] += 1
    return counts


def detect_log_anomalies(log_text: str) -> Dict[str, object]:
    """Detect simple anomalies in log text."""
    lines = log_text.splitlines()
    error_lines = [
        line for line in lines if re.search(r"\b(error|exception|panic|fatal)\b", line, re.IGNORECASE)
    ]
    anomaly = len(error_lines) >= max(3, len(lines) // 5) if lines else False
    return {
        "line_count": len(lines),
        "error_count": len(error_lines),
        "is_anomaly": anomaly,
        "sample_errors": error_lines[:5],
    }


def correlate_log_events(log_entries: Iterable[str]) -> Dict[str, object]:
    """Correlate log events by grouping similar messages."""
    normalized = []
    for entry in log_entries:
        normalized.append(re.sub(r"\d+", "<num>", entry.strip()))
    counts: Dict[str, int] = {}
    for entry in normalized:
        if not entry:
            continue
        counts[entry] = counts.get(entry, 0) + 1
    frequent = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5]
    return {"frequent_events": frequent, "unique_event_count": len(counts)}


def search_logs(
    keyword: str,
    log_type: str = "all",
    lines: int = 200,
    base_url: str | None = None,
    timeout: float = 5.0,
) -> List[str]:
    """Search logs for a keyword using VictoriaLogs or local files."""
    if base_url:
        response = query_victorialogs(query=keyword, base_url=base_url, limit=lines, timeout=timeout)
        return [json.dumps(response, ensure_ascii=True)]

    results: list[str] = []
    for path in _candidate_log_files(log_type):
        tail = _read_tail(path, lines)
        for line in tail.splitlines():
            if keyword.lower() in line.lower():
                results.append(f"{path}: {line}")
    return results


def _http_get_json(url: str, timeout: float = 5.0) -> Dict[str, object]:
    req = Request(url, method="GET")
    with urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return {"status": "error", "error": "invalid_json", "raw": payload}


def query_victorialogs(query: str, base_url: str | None = None, limit: int = 100, timeout: float = 5.0) -> Dict[str, object]:
    """Query VictoriaLogs using LogSQL query API."""
    url_base = base_url or _get_default_vl_url()
    params = {"query": query, "limit": limit}
    url = urljoin(url_base.rstrip("/") + "/", "select/logsql/query")
    url = f"{url}?{urlencode(params)}"
    return _http_get_json(url, timeout=timeout)


def query_otel_logs(query: str, query_url: str | None = None, limit: int = 100, timeout: float = 5.0) -> Dict[str, object]:
    """Query logs via an OTel log backend gateway with HTTP query API."""
    url_base = query_url or _get_default_otel_url()
    params = {"query": query, "limit": limit}
    url = url_base.rstrip("/") + "/api/v1/logs"
    url = f"{url}?{urlencode(params)}"
    return _http_get_json(url, timeout=timeout)
