# Docker Compose 测试环境与 Demo

## 启动环境
1. 启动服务
   - `docker compose up -d`
2. 检查服务
   - Prometheus: http://localhost:9090
   - Node Exporter: http://localhost:9100/metrics
   - VictoriaLogs: http://localhost:9428
   - OTel Collector: http://localhost:8889/metrics

## 写入示例日志（VictoriaLogs）
```bash
curl -X POST "http://localhost:9428/insert/jsonline" \
  -H "Content-Type: application/json" \
  --data-binary '{"_time":"2026-03-10T00:00:00Z","level":"error","msg":"demo error from service-a"}'
```

## Prometheus 查询示例
```bash
curl "http://localhost:9090/api/v1/query?query=up"
```

## AIOps 查询示例
```bash
uv run python main.py --query "CPU usage is high and requests are timing out"
```

## Skills CLI 示例
```bash
uv run python -m aiops.cli.skill_cli list
uv run python -m aiops.cli.skill_cli discover --query cpu --tag prometheus
```

## Skills API 示例
```bash
uv run python -m uvicorn aiops.api.skill_api:app --port 8000
curl "http://localhost:8000/skills"
curl "http://localhost:8000/skills/discover?query=cpu&tag=prometheus"
```

## 环境变量示例（可选）
```bash
export AIOPS_METRICS__PROMETHEUS_BASE_URL=http://localhost:9090
export AIOPS_LOGS__VICTORIALOGS_BASE_URL=http://localhost:9428
```
