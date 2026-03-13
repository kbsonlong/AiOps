# Tasks
- [x] Task 1: 统一配置前缀并补充启动校验
  - [x] 清理示例配置中的旧前缀，仅保留 `AIOPS_` 作为唯一入口
  - [x] 新增配置校验器与校验结果模型，并在入口处执行校验
  - [x] 为配置校验补充/调整单元测试

- [x] Task 2: 建立统一异常与错误处理策略
  - [x] 新增项目级异常基类与关键子类（配置/工作流/技能/代理）
  - [x] 将关键路径的裸异常捕获替换为统一错误处理（工作流与 API）
  - [x] 为错误处理补充测试（至少覆盖工作流 classify fallback 与 API 400/403/500 形态）

- [x] Task 3: 收敛意图识别并移除额外 LLM gate
  - [x] 以 classify 输出为准：确保 intent/language 写入 `state.context`
  - [x] 用确定性规则替代知识库 gate_synthesis 的额外 LLM 调用，满足“负向响应直返”策略
  - [x] 删除/调整与 IntentAgent 在工作流中的耦合（保留类作为可选能力不纳入工作流）
  - [x] 补充回归测试覆盖“知识库唯一来源且为负向响应”的返回行为

- [x] Task 4: 技能注册全局单例化并在工作流与 API 复用
  - [x] 新增全局技能注册表（懒加载 + 并发安全）
  - [x] 工作流 skill 编排节点复用全局注册表，不再每次 new Registry + bulk_register
  - [x] Skill API 的 registry 构建复用全局注册表
  - [x] 补充性能/行为回归测试（至少验证注册只发生一次）

- [x] Task 5: 增加健康检查与就绪探针端点
  - [x] 在现有 FastAPI 应用中新增 `/health` 与 `/ready`
  - [x] 健康检查覆盖关键依赖的可达性（按配置存在与否决定检查项）
  - [x] 为健康检查添加单元测试（使用 mock/monkeypatch，避免真实依赖）

# Task Dependencies
- Task 4 depends on Task 1 (如需从配置读取依赖地址/开关)
- Task 5 depends on Task 1 (读取依赖 URL 与超时配置)
