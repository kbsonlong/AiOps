# AIOps 文档索引

> 更新时间: 2025-03-20

## 📚 文档分类

### 🚀 快速开始

| 文档 | 描述 | 适合人群 |
|------|------|---------|
| [快速入门](./quickstart.md) | 5 分钟快速上手 | 新用户 |

### 🏗️ 架构设计

| 文档 | 描述 | 状态 |
|------|------|------|
| [系统架构](./architecture.md) | 完整系统架构文档 | ✅ 最新 |
| [任务分解与编排](./task_orchestration_design.md) | 新增任务编排系统 | ✅ 已实现 |
| [Agent Skills 设计](./agent_skills_design.md) | 技能系统设计 | ✅ 实现中 |
| [完整设计方案](./aiops_complete_design.md) | 原始完整设计 | 📖 参考 |

### 📖 API 参考

| 文档 | 描述 | 状态 |
|------|------|------|
| [API 参考](./api_reference.md) | 完整 API 文档 | ✅ v2.0 |
| [API 文档](./api.md) | REST API 文档 | 📖 参考 |

### 👥 用户指南

| 文档 | 描述 | 状态 |
|------|------|------|
| [用户指南](./user_guide.md) | 详细使用指南 | 📖 参考 |
| [部署指南](./deployment_guide_skills.md) | 生产环境部署 | 📖 参考 |
| [Docker 部署](./demo_docker_compose.md) | Docker Compose 示例 | 📖 参考 |

### 🔧 开发指南

| 文档 | 描述 | 状态 |
|------|------|------|
| [开发指南](./DEVELOPMENT.md) | 开发环境设置 | 📖 参考 |
| [实现计划](./implementation_plan.md) | 开发路线图 | 📖 参考 |

### 🔬 研究文档

| 文档 | 描述 | 状态 |
|------|------|------|
| [架构分析](./architecture_analysis.md) | 架构深度分析 | 📖 参考 |
| [架构优化提案](./architecture_optimization_proposals.md) | 优化方案 | ✅ 完成 |
| [意图识别研究](./intent_recognition_research_proposal.md) | 意图识别方案 | 📖 参考 |
| [LoRA 微调计划](./intent_lora_finetuning_plan.md) | 模型微调方案 | 📖 参考 |

### 🎓 Skills 自学习系统

| 文档 | 描述 | 状态 |
|------|------|------|
| [自学习系统设计 v2](./skills_self_learning_system_design_v2.md) | 最新设计方案 | 📋 计划中 |
| [实现任务 v2](./skills_self_learning_implementation_tasks_v2.md) | 开发任务清单 | 📋 计划中 |
| [自学习分析](./skills_self_learning_analysis.md) | 可行性分析 | 📖 参考 |

### 📢 其他设计

| 文档 | 描述 | 状态 |
|------|------|------|
| [智能客服设计](./intelligent_customer_service_design.md) | 客服系统设计 | 📖 参考 |
| [技能注册系统](./dynamic_skill_registration_system.md) | 动态注册机制 | 📖 参考 |

---

## 🆕 新增文档 (v2.0)

| 文档 | 描述 | 更新日期 |
|------|------|---------|
| [architecture.md](./architecture.md) | 完整系统架构，包含新增的任务编排系统 | 2025-03-20 |
| [task_orchestration_design.md](./task_orchestration_design.md) | 任务分解与编排详细设计 | 2025-03-20 |
| [api_reference.md](./api_reference.md) | 完整的 Python API 参考 | 2025-03-20 |
| [quickstart.md](./quickstart.md) | 快速入门指南 | 2025-03-20 |

---

## 📊 文档状态说明

| 状态 | 说明 |
|------|------|
| ✅ 最新 | 最新版本，推荐阅读 |
| ✅ 已实现 | 功能已实现并可用 |
| 📋 计划中 | 规划阶段，即将实现 |
| 📖 参考 | 历史文档，仅供参考 |
| 🔄 更新中 | 正在更新维护 |

---

## 🔍 按主题查找

### 任务编排系统
1. [任务分解与编排设计](./task_orchestration_design.md) - 详细设计
2. [系统架构](./architecture.md) - 整体集成

### Agent 系统
1. [系统架构](./architecture.md) - Agent 层设计
2. [完整设计方案](./aiops_complete_design.md) - 详细 Agent 定义

### Skills 系统
1. [Agent Skills 设计](./agent_skills_design.md) - 技能系统设计
2. [动态技能注册](./dynamic_skill_registration_system.md) - 注册机制
3. [自学习系统设计 v2](./skills_self_learning_system_design_v2.md) - 自学习功能

### 部署运维
1. [部署指南](./deployment_guide_skills.md) - 生产部署
2. [Docker Compose 示例](./demo_docker_compose.md) - 容器化部署
3. [快速入门](./quickstart.md) - 环境准备

---

## 🛠️ 贡献文档

### 文档规范

1. **Markdown 格式**：使用标准 Markdown 语法
2. **代码示例**：使用 Python 代码块
3. **版本标识**：在文档开头标注版本和更新日期
4. **状态标记**：使用状态标识符（✅、📋、📖）

### 提交文档

```bash
# 新增文档
docs/new_document.md

# 更新现有文档
git add docs/existing_document.md
git commit -m "docs: 更新 XXX 文档"
```

---

## 📧 反馈与建议

如果您发现文档问题或有改进建议：

1. 提交 GitHub Issue
2. 发送邮件至文档维护团队
3. 在讨论区发起讨论

---

> 维护者: AIOps 团队
> 最后更新: 2025-03-20
