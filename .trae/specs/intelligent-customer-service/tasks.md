# Tasks

- [x] Task 1: 环境与基础设施设置
    - [x] SubTask 1.1: 添加依赖 `langchain-chroma` 到 `pyproject.toml` 并安装（`langchain-litellm` 已存在）。
    - [x] SubTask 1.2: 创建目录结构 `knowledge/` 和 `data/vector_store`。

- [x] Task 2: 知识库核心实现
    - [x] SubTask 2.1: 实现 `DocumentProcessor`，使用 LangChain 加载器 (`TextLoader`, `UnstructuredMarkdownLoader`) 和分割器 (`RecursiveCharacterTextSplitter`)。
    - [x] SubTask 2.2: 实现 `VectorStoreManager`，使用 `langchain_chroma.Chroma` 和 `langchain_litellm.LiteLLMEmbeddings`。
    - [x] SubTask 2.3: 实现 `KnowledgeRetriever`，使用 LangChain 的检索器接口。
    - [x] SubTask 2.4: 创建脚本摄入示例/模拟数据（告警、手册）用于测试。

- [x] Task 3: 智能客服 Agent 实现
    - [x] SubTask 3.1: 使用 LangChain/LangGraph 定义 `CustomerServiceAgent` 类。
    - [x] SubTask 3.2: 创建 `query_knowledge_base` 工具，封装 LangChain 检索器。
    - [x] SubTask 3.3: 设计系统提示词（严格遵守“无幻觉”规则）。
    - [x] SubTask 3.4: 实现 `StrictAnswerValidator`（基础检查回答是否有依据）。

- [x] Task 4: 工作流集成
    - [x] SubTask 4.1: 更新 `main.py` 中的 `RouterState` 以包含 `knowledge_context`。
    - [x] SubTask 4.2: 实现 `customer_service_node` 函数。
    - [x] SubTask 4.3: 更新 `classify_query` 逻辑，将适当的查询路由至 `customer_service`。
    - [x] SubTask 4.4: 将新节点和边添加到 LangGraph 工作流中。

- [ ] Task 5: 验证与演示
    - [ ] SubTask 5.1: 创建测试脚本验证知识摄入。
    - [ ] SubTask 5.2: 创建测试脚本验证检索和回答。
    - [ ] SubTask 5.3: 运行完整工作流，测试示例查询（例如，“如何修复 CPU 高负载？”）。
