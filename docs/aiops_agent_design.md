# AIOps Agent 系统设计文档

## 概述

基于现有 LangGraph Router 模式，按照四个核心维度重新设计 AIOps Agent 系统：
1. **Metrics 监控维度** - 通过 Prometheus 和 OpenTelemetry 进行系统指标监控与分析
2. **日志分析维度** - 通过 VictoriaLogs 和 OpenTelemetry 进行日志收集、解析与异常检测
3. **故障分析维度** - 故障诊断与根因分析
4. **安全审计维度** - 安全监控与合规检查

## 当前架构分析

### 现有 Router 模式
- **Classification**: 定义路由决策，当前支持 `github`, `notion`, `slack` 三种源
- **RouterState**: 工作流状态管理
- **Agents**: 专用代理，各具工具和系统提示
- **Workflow**: 分类 → 路由 → 并行执行 → 合成

### 扩展点
1. 扩展 `Classification` 支持四个新维度
2. 替换 mock 工具为真实监控工具
3. 更新分类器提示以识别系统问题
4. 实现各维度专用工具

## 四个维度的 Agent 设计

### 1. Metrics 监控 Agent（云原生方案）

#### 职责
- 通过 Prometheus 查询系统指标（CPU、内存、磁盘、网络、进程、应用指标）
- 阈值检测与告警
- 趋势分析与容量预测
- 性能瓶颈识别
- 集成 OpenTelemetry 指标和 Trace 查询

#### 工具设计
```python
# Prometheus 查询工具
@tool
def query_prometheus_metrics(query: str, time_range: str = "5m") -> str:
    """查询 Prometheus 指标数据，支持 PromQL 查询语句"""

@tool
def get_metric_trend(metric_name: str, time_range: str = "1h") -> str:
    """获取指标趋势数据"""

@tool
def check_metric_threshold(metric: str, threshold: float, time_range: str = "5m") -> str:
    """检查指标是否超过阈值"""

@tool
def compare_metrics(metric1: str, metric2: str, time_range: str = "15m") -> str:
    """比较两个指标的关系和差异"""

@tool
def analyze_performance_bottlenecks(service: str = "all") -> str:
    """分析系统性能瓶颈"""

# OpenTelemetry 工具
@tool
def query_opentelemetry_traces(service_name: str, operation: str = None, time_range: str = "15m") -> str:
    """查询 OpenTelemetry Trace 数据"""

@tool
def get_service_metrics_from_otel(service: str, metric_type: str = "latency") -> str:
    """从 OpenTelemetry 获取服务指标"""

@tool
def correlate_metrics_traces(metric_name: str, trace_sample: int = 5) -> str:
    """关联指标数据和 Trace 数据进行分析"""
```

#### 系统提示
```
你是云原生指标监控专家，使用 Prometheus 和 OpenTelemetry 进行监控。负责：
1. 通过 PromQL 查询和分析系统及应用指标
2. 使用 OpenTelemetry 查询 Trace 和指标数据
3. 检测指标异常和阈值违规
4. 分析性能瓶颈和容量需求
5. 关联指标、日志和 Trace 数据进行根因分析

根据查询提供准确的指标分析和建议，使用 Prometheus 和 OpenTelemetry 作为数据源。
```

### 2. 日志分析 Agent（云原生方案）

#### 职责
- 通过 VictoriaLogs 查询和分析系统/应用日志
- 日志模式识别与异常检测
- 错误跟踪与根本原因分析
- 日志关联与事件链重构
- 集成 OpenTelemetry 日志查询

#### 工具设计
```python
# VictoriaLogs 查询工具
@tool
def query_victorialogs(logql_query: str, time_range: str = "15m", limit: int = 100) -> str:
    """使用 LogQL 查询 VictoriaLogs 日志数据"""

@tool
def search_logs_by_keyword(keyword: str, service: str = None, time_range: str = "1h") -> str:
    """根据关键词搜索日志"""

@tool
def analyze_log_patterns(service: str, time_range: str = "30m") -> str:
    """分析日志模式，识别常见错误和警告模式"""

@tool
def detect_log_anomalies(service: str, time_range: str = "1h") -> str:
    """检测日志异常，如错误率激增、异常模式等"""

@tool
def correlate_logs_with_metrics(log_pattern: str, metric_name: str, time_range: str = "30m") -> str:
    """关联日志模式和指标数据"""

@tool
def trace_request_flow(request_id: str = None, trace_id: str = None) -> str:
    """跟踪请求在系统中的完整流程（跨服务日志）"""

# OpenTelemetry 日志工具
@tool
def query_otel_logs(service_name: str, severity: str = "ERROR", time_range: str = "15m") -> str:
    """查询 OpenTelemetry 收集的日志"""

@tool
def get_log_statistics(service: str, time_range: str = "1h") -> str:
    """获取日志统计信息（错误率、警告率、信息量等）"""
```

#### 系统提示
```
你是云原生日志分析专家，使用 VictoriaLogs 和 OpenTelemetry 进行日志分析。负责：
1. 通过 LogQL 查询 VictoriaLogs 中的日志数据
2. 使用 OpenTelemetry 查询分布式追踪和日志
3. 识别日志异常模式和错误趋势
4. 关联日志、指标和 Trace 数据进行根因分析
5. 跟踪请求在微服务架构中的完整流程

根据查询提供详细的日志分析和故障诊断见解。
```

### 3. 故障分析 Agent

#### 职责
- 故障检测与分类
- 根本原因分析
- 影响评估与优先级划分
- 解决方案推荐与验证

#### 工具设计
```python
@tool
def diagnose_fault(symptoms: str) -> str:
    """诊断故障原因"""

@tool
def analyze_root_cause(metrics: dict, logs: list) -> str:
    """分析根本原因"""

@tool
def assess_impact(fault_type: str) -> str:
    """评估故障影响"""

@tool
def recommend_solutions(fault_analysis: str) -> str:
    """推荐解决方案"""

@tool
def validate_solution(solution: str, fault_context: str) -> str:
    """验证解决方案有效性"""
```

#### 系统提示
```
你是故障诊断专家。负责：
1. 分析和诊断系统故障
2. 识别根本原因和影响因素
3. 评估故障严重性和影响范围
4. 推荐验证过的解决方案

根据查询提供全面的故障分析和修复建议。
```

### 4. 安全审计 Agent

#### 职责
- 安全配置检查
- 漏洞扫描与风险评估
- 访问控制审计
- 威胁检测与事件响应

#### 工具设计
```python
@tool
def scan_vulnerabilities(target: str = "localhost") -> str:
    """扫描系统漏洞"""

@tool
def check_security_config(config_type: str) -> str:
    """检查安全配置"""

@tool
def audit_access_logs(user: str = None) -> str:
    """审计访问日志"""

@tool
def detect_security_threats(logs: list, metrics: dict) -> str:
    """检测安全威胁"""

@tool
def assess_compliance(standard: str = "baseline") -> str:
    """评估合规性"""
```

#### 系统提示
```
你是安全审计专家。负责：
1. 监控系统安全状态和配置
2. 检测安全威胁和异常访问
3. 进行合规性检查和风险评估
4. 提供安全加固建议

根据查询提供详细的安全分析和建议。
```

## 协作机制设计

### 1. 多 Agent 协作模式
- **并行协作**: 多个 Agent 同时分析不同方面
- **顺序协作**: 一个 Agent 的输出作为另一个的输入
- **共识协作**: 多个 Agent 投票决定最佳方案
- **分级协作**: 主 Agent 协调专业 Agent

### 2. 工作流扩展
```python
# 扩展 Classification 支持四个维度
class Classification(TypedDict):
    source: Literal["metrics", "logs", "fault", "security", "github", "notion", "slack"]
    query: str
    severity: Literal["critical", "high", "medium", "low"]  # 新增严重程度
```

### 3. 状态管理扩展
```python
class RouterState(TypedDict):
    query: str
    classifications: list[Classification]
    results: Annotated[list[AgentOutput], operator.add]
    final_answer: str
    system_metrics: dict  # 新增：系统指标
    log_data: list[str]   # 新增：日志数据
    fault_context: dict   # 新增：故障上下文
    security_status: dict # 新增：安全状态
```

## 实施步骤

### 第一阶段：基础架构准备
1. **依赖更新**：安装 Prometheus 客户端、VictoriaLogs 查询所需库、OpenTelemetry SDK 及相关依赖
2. **目录结构**：创建模块化目录
3. **配置系统**：实现环境配置管理

### 第二阶段：工具实现
1. **Metrics 工具**：实现 Prometheus 查询工具和 OpenTelemetry 集成
2. **日志工具**：实现 VictoriaLogs 查询工具和 OpenTelemetry 日志查询
3. **故障工具**：实现诊断和根因分析工具
4. **安全工具**：实现安全检查和审计工具

### 第三阶段：Agent 实现
1. **Metrics Agent**：实现指标监控 Agent
2. **日志 Agent**：实现日志分析 Agent
3. **故障 Agent**：实现故障分析 Agent
4. **安全 Agent**：实现安全审计 Agent

### 第四阶段：工作流集成
1. **分类器更新**：扩展分类器支持四个维度
2. **工作流扩展**：更新 LangGraph 工作流
3. **协作机制**：实现多 Agent 协作
4. **接口集成**：实现 CLI/API 接口

### 第五阶段：测试验证
1. **单元测试**：各工具和 Agent 测试
2. **集成测试**：工作流集成测试
3. **性能测试**：监控开销测试
4. **安全测试**：安全控制测试

## 依赖关系

### 核心依赖
```toml
# pyproject.toml 更新
dependencies = [
    "langchain[openai]>=1.2.10",
    "langgraph>=1.0.10",
    "prometheus-api-client>=0.5.0",  # Prometheus 查询客户端
    "requests>=2.31.0",              # HTTP 客户端，用于 VictoriaLogs 等 API 查询
    "opentelemetry-api>=1.25.0",     # OpenTelemetry API
    "opentelemetry-sdk>=1.25.0",     # OpenTelemetry SDK
    "opentelemetry-exporter-prometheus>=1.25.0", # Prometheus exporter
    "pydantic>=2.0.0",        # 配置验证
    "schedule>=1.2.0",        # 定时任务
    "pyyaml>=6.0",           # 配置文件
    "python-dotenv>=1.0.0",  # 环境变量
    "structlog>=24.0.0",     # 结构化日志
]
```

### 可选依赖（根据需求添加）
```toml
# 高级功能可选
optional-dependencies = {
    "advanced-monitoring": [
        "prometheus-client>=0.20.0",  # Prometheus 集成
        "influxdb>=5.3.0",           # 时序数据库
    ],
    "advanced-logging": [
        "elasticsearch>=8.0.0",      # Elasticsearch 集成
        "opensearch-py>=2.0.0",      # OpenSearch 集成
    ],
    "security": [
        "bandit>=1.7.0",             # 代码安全扫描
        "safety>=2.0.0",             # 依赖安全扫描
    ],
}
```

## 文件结构

```
aiops/
├── main.py                    # 主入口，工作流编排
├── config/                    # 配置管理
│   ├── __init__.py
│   ├── settings.py           # 主配置
│   ├── metrics_config.py     # 指标配置
│   ├── logs_config.py        # 日志配置
│   └── security_config.py    # 安全配置
├── agents/                   # Agent 实现
│   ├── __init__.py
│   ├── base_agent.py         # 基础 Agent 类
│   ├── metrics_agent.py      # Metrics 监控 Agent
│   ├── logs_agent.py         # 日志分析 Agent
│   ├── fault_agent.py        # 故障分析 Agent
│   └── security_agent.py     # 安全审计 Agent
├── tools/                    # 工具实现
│   ├── __init__.py
│   ├── metrics_tools.py      # 指标监控工具
│   ├── logs_tools.py         # 日志分析工具
│   ├── fault_tools.py        # 故障分析工具
│   └── security_tools.py     # 安全审计工具
├── workflows/               # 工作流定义
│   ├── __init__.py
│   ├── router_workflow.py   # 主路由工作流
│   ├── collaboration_workflow.py # 协作工作流
│   └── escalation_workflow.py    # 升级工作流
├── data/                   # 数据管理
│   ├── __init__.py
│   ├── collectors.py       # 数据收集器
│   └── processors.py       # 数据处理器
├── security/              # 安全控制
│   ├── __init__.py
│   ├── controller.py      # 安全控制器
│   ├── audit_logger.py    # 审计日志
│   └── approval_system.py # 审批系统
├── notifications/         # 通知系统
│   ├── __init__.py
│   ├── notifier.py       # 通知器
│   └── templates.py      # 通知模板
└── utils/                # 工具函数
    ├── __init__.py
    ├── validators.py     # 验证器
    ├── formatters.py     # 格式化器
    └── helpers.py        # 辅助函数
```

## 风险与缓解措施

### 技术风险
1. **性能开销**：监控 Agent 可能占用过多资源
   - 缓解：优化采集频率，使用轻量级检查

2. **误报问题**：Agent 可能产生误报
   - 缓解：实现确认机制，使用多 Agent 共识

3. **安全风险**：工具可能被滥用
   - 缓解：严格的权限控制，操作审批流程

### 实施风险
1. **集成复杂度**：四个维度 Agent 协同工作复杂
   - 缓解：分阶段实施，先独立后集成

2. **维护成本**：多 Agent 系统维护复杂
   - 缓解：模块化设计，清晰接口定义

## 成功指标

### 功能指标
1. **监控覆盖率**：系统关键指标监控覆盖率 ≥ 95%
2. **检测准确率**：异常检测准确率 ≥ 90%
3. **响应时间**：问题检测到告警 ≤ 30秒
4. **诊断准确率**：根因分析准确率 ≥ 85%

### 性能指标
1. **资源占用**：监控系统 CPU 占用 < 2%
2. **内存占用**：监控系统内存占用 < 200MB
3. **存储占用**：日志数据日增长 < 1GB

## 下一步行动

### 待确认事项
1. [ ] Agent 职责划分是否合理
2. [ ] 工具设计是否满足需求
3. [ ] 协作机制是否有效
4. [ ] 实施优先级和范围

### 实施前提
1. [ ] 用户确认本设计文档
2. [ ] 环境准备完成
3. [ ] 测试计划制定
4. [ ] 回滚方案准备

---

*文档版本：1.0*
*创建日期：2026-03-10*
*更新记录：初始版本*