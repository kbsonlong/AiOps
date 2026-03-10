# 智能客服功能设计方案 (Intelligent Customer Service Spec)

## Why
当前 AIOps 系统虽然可以将查询路由到特定 Agent（GitHub, Notion, Slack），但缺乏一个能够基于历史告警、故障报告和运维手册回答通用运维问题的集中式“知识库”。运维人员经常询问重复性问题，如果这些知识被索引并可访问，这些问题本可以自动回答。

## What Changes
- **新增知识库模块 (New Knowledge Base Module)**:
    - **文档处理**: 使用 LangChain 的文档加载器 (`TextLoader`, `UnstructuredMarkdownLoader`) 和文本分割器 (`RecursiveCharacterTextSplitter`) 处理文本/Markdown 文件。
    - **向量存储**: 使用 `langchain-chroma` 库作为向量存储后端。
    - **向量化 (Embeddings)**: 使用 `langchain-litellm` (LiteLLMEmbeddings) 调用嵌入模型。
    - **检索**: 使用 LangChain 的检索器接口实现混合检索（语义 + 关键词）。
- **新增智能客服 Agent (New Customer Service Agent)**:
    - **角色**: 严格基于检索到的上下文回答用户问题。
    - **行为**: 如果未找到相关信息，明确回复“不知道”（杜绝幻觉）。
    - **工具**: `query_knowledge_base` 工具，通过 LangChain 访问向量库。
- **工作流集成 (Workflow Integration)**:
    - 更新 `RouterState` 以包含知识库上下文。
    - 在 LangGraph 工作流中添加 `customer_service` 节点。
    - 添加路由逻辑，将通用/咨询类查询路由至此新 Agent。

## Impact
- **依赖**: 新增 `langchain-chroma`。已存在 `langchain-litellm`。
- **文件结构**:
    - 新增目录 `knowledge/` 用于知识库核心逻辑。
    - 新增 Agent 定义文件 `agents/customer_service.py`。
- **工作流**: `main.py` 中的主图将增加一个用于客服的分支。

## ADDED Requirements

### Requirement: Knowledge Base
系统必须支持使用 LangChain 的 Document Loaders 和 Text Splitters 摄入文本/Markdown 文档。
系统必须使用 `langchain-chroma` 存储向量嵌入。
系统必须使用 `langchain-litellm` 提供嵌入服务。

### Requirement: Customer Service Agent
Agent 必须仅使用检索到的上下文回答用户问题。
如果置信度低或未找到上下文，Agent 必须返回标准的“不知道”回复。
Agent 必须引用信息的来源（例如，“基于告警 #123”）。

### Requirement: Routing
路由器必须识别“咨询类”或“如何做”类查询，并将其路由至客服 Agent。
