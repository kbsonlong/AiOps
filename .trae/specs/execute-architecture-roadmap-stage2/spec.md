# 架构优化路线图（第二阶段）Spec

## Why
第一阶段已完成配置/异常/路由与技能注册等基础优化。第二阶段聚焦“架构增强”，目标是在不引入不必要外部耦合的前提下，为知识库、性能与扩展性提供可演进的模块化底座：向量存储配置解耦、缓存层、事件总线与中间件链。

## What Changes
- 向量存储配置解耦：将嵌入模型与向量库相关配置纳入统一配置体系（`Settings`），避免散落环境变量与硬编码
- 缓存层：提供统一缓存接口与默认内存 TTL 实现，用于缓存高频计算（例如技能推荐/组合计划等）
- 事件总线：提供进程内异步事件发布/订阅机制，用于解耦统计、审计、观测等横切关注点
- 中间件链：引入可组合的中间件链机制，将现有工作流中的硬编码中间件节点演进为可插拔链式执行
- **约束**：健康检查探针仅做“应用自检”，不得新增对外部组件连通性探测（Prometheus/Redis/ChromaDB 等）
- **非目标**：依赖注入容器/沙箱强化/敏感数据加密/更重的外部缓存后端，留到第三阶段或后续迭代

## Impact
- Affected specs: 配置管理、知识库系统、性能优化、工作流系统、可观测与扩展点
- Affected code:
  - 配置：aiops/config/settings.py（新增 knowledge/embeddings 配置模型并纳入 Settings）
  - 知识库：aiops/knowledge/vector_store.py（从 Settings 读取配置；保留现有环境变量作为兼容层，若需要）
  - 缓存：aiops/cache/*（新增模块；默认仅内存 TTL 实现）
  - 事件：aiops/core/events.py（新增事件总线）
  - 工作流：aiops/workflows/*（新增 middleware_chain.py；迁移 skill_middleware_pre/post）
  - API：aiops/api/skill_api.py（保持 /health 与 /ready 为自检，不引入外部探测）
  - 测试：tests/（新增/调整缓存、事件总线、中间件链、向量配置相关用例）

## ADDED Requirements
### Requirement: 向量存储配置解耦
系统 SHALL 将向量存储与嵌入模型配置纳入 `Settings`，并在 `VectorStoreManager` 初始化时优先使用 `Settings` 配置。

#### Scenario: 使用 Settings 配置
- **WHEN** 系统提供 `Settings.knowledge.embeddings` 配置
- **THEN** `VectorStoreManager` 使用该配置创建 embeddings 与向量库连接参数

#### Scenario: 兼容环境变量（可选）
- **WHEN** 未提供 `Settings.knowledge.embeddings` 配置但存在历史环境变量
- **THEN** 系统可回退读取历史环境变量（保持行为兼容），且不引入硬编码默认值冲突

### Requirement: 缓存层（默认内存 TTL）
系统 SHALL 提供缓存接口与默认内存 TTL 实现，支持 `get/set/delete` 与 `get_or_set`，并能在关键路径上用于减少重复计算。

#### Scenario: 命中缓存
- **WHEN** 请求命中有效 TTL
- **THEN** 直接返回缓存值且不执行工厂函数

#### Scenario: 缓存过期
- **WHEN** TTL 已过期
- **THEN** 重新计算并更新缓存

### Requirement: 事件总线（进程内异步）
系统 SHALL 提供进程内异步事件总线，支持发布事件与订阅处理器（同步或异步），并保证单个处理器异常不影响其他处理器执行。

#### Scenario: 发布与订阅
- **WHEN** 发布一个事件
- **THEN** 所有已订阅该事件类型的处理器都会被调用

### Requirement: 中间件链机制
系统 SHALL 提供可组合的中间件链，用于在工作流执行前后插入横切逻辑（如技能上下文注入、结果固化等），并支持按顺序执行与短路返回。

#### Scenario: 链式执行
- **WHEN** 链中包含多个中间件
- **THEN** 按添加顺序执行，最终返回链的输出上下文

### Requirement: 健康探针不耦合外部组件
系统 SHALL 保证 `/health` 与 `/ready` 仅执行应用自检（例如配置有效性、自身依赖注入状态），不得新增对外部组件连通性探测。

## MODIFIED Requirements
### Requirement: 工作流中间件接入方式
系统 SHALL 将工作流中间件由“固定节点”演进为“可配置的中间件链”，并保持现有工作流对外行为一致（结果字段与主要路由不变）。

## REMOVED Requirements
### Requirement: 在健康探针中探测外部依赖连通性
**Reason**: 健康探针应只反映应用自身可运行性，外部依赖连通性应交由独立监控系统处理，避免运行时耦合与不稳定。
**Migration**: 若未来需要外部依赖连通性检查，新增独立的诊断技能或运维脚本，而不是放入 `/health` 与 `/ready`。
