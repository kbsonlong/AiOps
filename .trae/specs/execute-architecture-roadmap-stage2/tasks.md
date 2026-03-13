# Tasks
- [x] Task 1: 向量存储配置解耦并纳入 Settings
  - [x] 在 aiops/config/ 下新增 knowledge/embeddings 配置模型并纳入 Settings
  - [x] 调整 VectorStoreManager 支持从 Settings 读取 embeddings 与存储参数
  - [x] 为配置读取与回退逻辑补充单元测试

- [x] Task 2: 新增缓存层并在关键路径接入
  - [x] 定义缓存接口与内存 TTL 实现（不引入外部依赖）
  - [x] 在至少一个高频路径接入缓存（例如技能发现/组合计划），并提供开关
  - [x] 添加缓存命中/过期的单元测试

- [x] Task 3: 引入进程内事件总线并接入统计/审计点
  - [x] 实现事件类型基类与 EventBus（异步队列 + 订阅机制）
  - [x] 在至少一个关键点发布事件（例如技能执行/工作流节点执行）
  - [x] 添加事件发布与异常隔离的单元测试

- [x] Task 4: 实现中间件链机制并迁移现有工作流中间件
  - [x] 实现 middleware_chain（可组合、可短路、支持 async）
  - [x] 将 skill_middleware_pre/post 的现有逻辑迁移为链式中间件
  - [x] 确保工作流对外行为兼容并补充回归测试

- [x] Task 5: 约束健康探针为应用自检（不引入外部探测）
  - [x] 确认 /health 与 /ready 不包含外部组件连通性探测逻辑
  - [x] 添加单测防回归（例如 mock 网络函数并断言不被调用）

# Task Dependencies
- Task 2 depends on Task 4（若缓存作为中间件挂载则需要先有链机制；否则可并行）
- Task 3 can be parallel with Task 2（事件总线与缓存互不依赖）
