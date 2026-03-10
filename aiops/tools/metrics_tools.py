from __future__ import annotations

import json
from typing import Dict, Optional
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from aiops.config.settings import load_settings


def _get_default_base_url() -> str:
    return load_settings().metrics.prometheus_base_url


def detect_metric_anomaly(metric: float, threshold: float = 80.0) -> Dict[str, object]:
    """Detect whether a metric crosses a threshold."""
    return {
        "metric": float(metric),
        "threshold": float(threshold),
        "is_anomaly": float(metric) >= float(threshold),
    }


def _http_get_json(url: str, timeout: float = 5.0) -> Dict[str, object]:
    req = Request(url, method="GET")
    with urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return {"status": "error", "error": "invalid_json", "raw": payload}


def _extract_prom_value(payload: Dict[str, object]) -> Optional[float]:
    try:
        data = payload.get("data", {})  # type: ignore[assignment]
        result = data.get("result", [])  # type: ignore[assignment]
        if not result:
            return None
        value = result[0].get("value")  # type: ignore[index]
        if not value or len(value) < 2:
            return None
        return float(value[1])
    except (ValueError, AttributeError, TypeError):
        return None


def query_prometheus(query: str, base_url: Optional[str] = None, time: Optional[float] = None, timeout: float = 5.0) -> Dict[str, object]:
    """Query Prometheus instant query API."""
    url_base = base_url or _get_default_base_url()
    params = {"query": query}
    if time is not None:
        params["time"] = time
    url = urljoin(url_base.rstrip("/") + "/", "api/v1/query")
    url = f"{url}?{urlencode(params)}"
    return _http_get_json(url, timeout=timeout)


def query_prometheus_range(
    query: str,
    base_url: Optional[str] = None,
    start: float = 0.0,
    end: float = 0.0,
    step: float = 0.0,
    timeout: float = 5.0,
) -> Dict[str, object]:
    """Query Prometheus range query API."""
    url_base = base_url or _get_default_base_url()
    params = {"query": query, "start": start, "end": end, "step": step}
    url = urljoin(url_base.rstrip("/") + "/", "api/v1/query_range")
    url = f"{url}?{urlencode(params)}"
    return _http_get_json(url, timeout=timeout)


def query_otel_metrics(query: str, query_url: Optional[str] = None, time: Optional[float] = None, timeout: float = 5.0) -> Dict[str, object]:
    """Query metrics via an OTel stack exposing Prometheus-compatible query APIs."""
    url_base = query_url or load_settings().metrics.otel_metrics_query_url
    params = {"query": query}
    if time is not None:
        params["time"] = time
    url = url_base.rstrip("/") + "/api/v1/query"
    url = f"{url}?{urlencode(params)}"
    return _http_get_json(url, timeout=timeout)


def collect_cpu_metrics(base_url: Optional[str] = None, query: Optional[str] = None, timeout: float = 5.0) -> Dict[str, object]:
    """Collect CPU usage via Prometheus."""
    url_base = base_url or _get_default_base_url()
    promql = query or '100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
    payload = query_prometheus(promql, base_url=url_base, timeout=timeout)
    return {"cpu_percent": _extract_prom_value(payload), "raw": payload}


def collect_memory_metrics(base_url: Optional[str] = None, query: Optional[str] = None, timeout: float = 5.0) -> Dict[str, object]:
    """Collect memory usage via Prometheus."""
    url_base = base_url or _get_default_base_url()
    promql = query or "100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))"
    payload = query_prometheus(promql, base_url=url_base, timeout=timeout)
    return {"memory_percent": _extract_prom_value(payload), "raw": payload}


def collect_disk_metrics(base_url: Optional[str] = None, query: Optional[str] = None, timeout: float = 5.0) -> Dict[str, object]:
    """Collect disk usage via Prometheus."""
    url_base = base_url or _get_default_base_url()
    promql = query or (
        '100 * (1 - (node_filesystem_free_bytes{fstype!~"tmpfs|overlay"} '
        '/ node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}))'
    )
    payload = query_prometheus(promql, base_url=url_base, timeout=timeout)
    return {"disk_percent": _extract_prom_value(payload), "raw": payload}


def collect_network_metrics(
    base_url: Optional[str] = None,
    recv_query: Optional[str] = None,
    sent_query: Optional[str] = None,
    timeout: float = 5.0,
) -> Dict[str, object]:
    """Collect network throughput via Prometheus."""
    url_base = base_url or _get_default_base_url()
    recv_promql = recv_query or 'sum(irate(node_network_receive_bytes_total[5m]))'
    sent_promql = sent_query or 'sum(irate(node_network_transmit_bytes_total[5m]))'
    recv_payload = query_prometheus(recv_promql, base_url=url_base, timeout=timeout)
    sent_payload = query_prometheus(sent_promql, base_url=url_base, timeout=timeout)
    return {
        "bytes_recv_per_sec": _extract_prom_value(recv_payload),
        "bytes_sent_per_sec": _extract_prom_value(sent_payload),
        "raw": {"recv": recv_payload, "sent": sent_payload},
    }


def collect_process_metrics(
    base_url: Optional[str] = None,
    query: Optional[str] = None,
    timeout: float = 5.0,
) -> Dict[str, object]:
    """Collect process-level metrics via Prometheus exporters."""
    url_base = base_url or _get_default_base_url()
    promql = query or "topk(5, process_cpu_seconds_total)"
    payload = query_prometheus(promql, base_url=url_base, timeout=timeout)
    return {"top_processes": payload.get("data", {}).get("result", []), "raw": payload}
