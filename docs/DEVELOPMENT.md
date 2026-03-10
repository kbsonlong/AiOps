# AIOps 开发环境指南

本项目使用 Docker Compose 管理开发环境，包括数据库、监控服务和本地大模型（Ollama）。

## 1. 启动服务

使用以下命令启动所有依赖服务（包括 Ollama）：

```bash
docker-compose up -d
```

这将启动：
- Prometheus (9090)
- VictoriaLogs (9428)
- OTEL Collector (4318)
- ChromaDB (8000)
- Redis (6379)
- Ollama (11434)
- AIOps 应用 (8080/8081)

## 2. 初始化 Ollama 模型

首次启动后，你需要拉取 `llama3` 模型：

```bash
# 进入 Ollama 容器并拉取模型
docker exec -it aiops-ollama-1 ollama pull llama3
```

或者如果你在本地安装了 Ollama CLI 且指向了容器端口：
```bash
OLLAMA_HOST=http://localhost:11434 ollama pull llama3
```

## 3. 本地开发

本项目使用 `uv` 管理依赖。

### 安装依赖

```bash
uv sync
```

### 运行应用

你可以直接运行 Python 脚本，它会自动读取 `.env` 文件配置连接到本地暴露的服务端口：

```bash
uv run python main.py --query "系统负载很高怎么办？"
```

### 环境变量

`.env` 文件已自动生成，配置了本地开发所需的环境变量。
如果你在 Docker 内部运行，服务会自动使用内部网络别名（如 `http://ollama:11434`）。
