# AIOps Agent 用户指南

## 快速开始
1. 安装依赖
   - `uv sync`
2. 运行示例
   - `python main.py`

## 常见用法
- Metrics 查询：通过 Prometheus/OTel 查询 CPU、内存、磁盘、网络指标。
- 日志查询：通过 VictoriaLogs/OTel 查询日志或本地采集。
- 故障分析：输入症状，获得根因与建议。
- 安全审计：支持访问日志审计与合规评估。

## 配置
配置字段在 `aiops/config/*.py`，可通过环境变量覆盖，例如：
- `AIOPS_METRICS__PROMETHEUS_BASE_URL`
- `AIOPS_LOGS__VICTORIALOGS_BASE_URL`

