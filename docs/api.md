# AIOps Agent API 参考

## 工具接口

### Metrics
- `collect_cpu_metrics(base_url, query=None, timeout=5.0)`
- `collect_memory_metrics(base_url, query=None, timeout=5.0)`
- `collect_disk_metrics(base_url, query=None, timeout=5.0)`
- `collect_network_metrics(base_url, recv_query=None, sent_query=None, timeout=5.0)`
- `collect_process_metrics(base_url, query=None, timeout=5.0)`
- `query_prometheus(query, base_url, time=None, timeout=5.0)`
- `query_prometheus_range(query, base_url, start, end, step, timeout=5.0)`
- `query_otel_metrics(query, query_url, time=None, timeout=5.0)`

### Logs
- `collect_system_logs(log_type="syslog", lines=100, base_url=None, query=None, timeout=5.0)`
- `search_logs(keyword, log_type="all", lines=200, base_url=None, timeout=5.0)`
- `query_victorialogs(query, base_url, limit=100, timeout=5.0)`
- `query_otel_logs(query, query_url, limit=100, timeout=5.0)`
- `analyze_log_patterns(log_text)`
- `detect_log_anomalies(log_text)`
- `correlate_log_events(log_entries)`

### Fault
- `diagnose_fault(symptoms)`
- `analyze_root_cause(metrics, logs)`
- `assess_impact(fault_type)`
- `recommend_solutions(fault_analysis)`
- `validate_solution(solution, fault_context)`

### Security
- `scan_vulnerabilities(target="localhost")`
- `check_security_config(config_type)`
- `audit_access_logs(user=None)`
- `detect_security_threats(logs, metrics)`
- `assess_compliance(standard="baseline")`

