# 架构优化路线图（第一阶段） Spec

## Why
当前项目已具备较好的模块化基础，但在配置、错误处理、技能注册与健康检查方面存在可维护性与性能隐患。第一阶段聚焦 P0/P1 项，先把“稳定性与可运维性底座”补齐，降低后续阶段改造成本。

## What Changes
- 统一环境变量与配置入口：以 `AIOPS_` 为唯一前缀，并在启动阶段执行配置校验
- 建立统一异常体系与错误处理：减少裸 `except Exception`，保证可观测与可定位
- 收敛意图识别：以路由分类输出为准，移除额外 LLM gate 调用（以确定性规则替代）
- 技能注册单例化：内置技能注册只做一次，工作流与 API 复用同一全局注册表
- 新增健康检查与就绪探针端点：提供依赖连通性与整体健康状态
- **非目标**：第二/三阶段（缓存/事件总线/中间件链/DI/沙箱强化/加密等）不在本变更内实现

## Impact
- Affected specs: 配置管理、错误处理、技能系统、工作流路由、API 运维端点
- Affected code:
  - 配置：aiops/config/settings.py、.env.example
  - 工作流：aiops/workflows/router_workflow.py
  - 技能系统：aiops/skills/registry.py、aiops/api/skill_api.py
  - API：aiops/api/skill_api.py（新增健康端点）
  - 测试：tests/test_config.py、tests/test_workflows.py、tests/test_skills_api.py（新增/调整用例）

## ADDED Requirements
### Requirement: 配置验证层
系统 SHALL 在启动时对配置进行一致性与必需项校验，并在配置不合法时给出可读的错误信息。

#### Scenario: 配置合法
- **WHEN** 系统加载配置（来自文件与 `AIOPS_` 环境变量）
- **THEN** 校验通过，系统继续启动并可正常处理请求/工作流调用

#### Scenario: 配置不合法
- **WHEN** 系统加载配置但缺少关键配置（例如 metrics/logs 的 base_url）
- **THEN** 系统返回明确的校验错误信息（包含缺失项列表），并拒绝继续启动或在调用入口处失败（取决于入口类型）

### Requirement: 全局技能注册表
系统 SHALL 提供进程级全局技能注册表，内置技能在同一进程内只注册一次，并支持在运行时查询已注册技能集合。

#### Scenario: 多次调用不重复注册
- **WHEN** 工作流多次执行或 API 多次请求触发技能发现/列举
- **THEN** 技能注册仅发生一次，后续请求复用同一注册表实例

### Requirement: 健康检查与就绪端点
系统 SHALL 提供 `/health` 与 `/ready` 端点用于健康检查与就绪探针。

#### Scenario: 依赖健康
- **WHEN** 调用 `/health`
- **THEN** 返回整体状态为 `healthy`，并包含关键依赖的检查结果（至少包含 Prometheus / VictoriaLogs / ChromaDB / Redis 的可达性检查，若配置存在）

#### Scenario: 依赖不健康
- **WHEN** 任一关键依赖不可达或超时
- **THEN** `/health` 返回整体状态为 `unhealthy` 或 `degraded`（按规则定义），且 `/ready` 返回 503

## MODIFIED Requirements
### Requirement: 路由分类与意图信息
系统 SHALL 以 `classify_query` 的结构化输出为唯一“意图/语言”来源，并将其写入 `state.context` 供下游使用（如响应格式、后续能力扩展）。

### Requirement: 知识库负向响应防幻觉
系统 SHALL 在知识库为唯一信息源且其结果为“无法回答/未知/未包含”时，直接返回该负向响应，不再通过额外 LLM gate 决策。

## REMOVED Requirements
### Requirement: 兼容旧版 `APP_*` 配置前缀
**Reason**: 代码已以 `AIOPS_` 为默认前缀，`APP_*` 仅残留在示例配置中，会造成维护混乱与错误配置风险。
**Migration**: 删除/迁移 `.env.example` 中的 `APP_*` 配置；若外部系统仍使用旧前缀，统一改为 `AIOPS_` 并使用双下划线层级分隔（例如 `AIOPS_METRICS__PROMETHEUS_BASE_URL`）。
