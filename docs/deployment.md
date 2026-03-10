# AIOps Agent 部署指南

## 运行环境
- Python 3.12
- uv 包管理器
- Prometheus（metrics）
- VictoriaLogs 或 OTel 日志后端（logs）

## 配置建议
1. 配置 Prometheus 基础地址
2. 配置 VictoriaLogs 查询地址
3. 通过环境变量注入认证信息（如有）

## 启动
- 本地启动：`python main.py`

