*- [x] 依赖 `langchain-chroma` 已安装并正常工作，`langchain-litellm` 用于嵌入。

*- [x] `DocumentProcessor` 正确使用 LangChain 加载器和分割器处理示例文档。
- [x] `VectorStoreManager` 使用 `langchain_chroma.Chroma` 保存和加载嵌入。
- [x] `KnowledgeRetriever` 通过 LangChain 检索器接口返回相关文档。

*- [x] 客服 Agent 正确回答知识库中存在的问题。
- [x] 客服 Agent 正确拒绝回答知识库中不存在的无意义问题。
- [x] `main.py` 工作流将“如何...”类问题路由至客服节点。
- [x] 最终回复包含信息来源。

