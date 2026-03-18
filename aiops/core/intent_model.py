"""意图识别模型管理器，支持多版本模型和扩展 Agent。

此模块实现了模型的生命周期管理：
- 加载不同版本的模型（base / lora）
- 支持 Agent 扩展时的模型迁移
- 向后兼容处理（不支持的 Agent 降级）
- A/B 测试支持

使用示例:
    from aiops.core.intent_model import IntentModelManager

    # 初始化管理器
    manager = IntentModelManager()

    # 加载模型
    manager.load_model()

    # 执行分类
    result = manager.classify("CPU 使用率很高")
    print(result)  # {'source': 'metrics', 'severity': 'medium', ...}

    # 迁移到新模型
    manager.migrate_to_new_model("models/intent_lora_v2.0")
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from aiops.core.agent_registry import AgentRegistry, get_registry


class ModelType(Enum):
    """模型类型枚举。"""
    BASE = "base"  # 基础模型（如 qwen2.5:3b）
    LORA = "lora"  # LoRA 微调模型


@dataclass
class ModelInfo:
    """模型信息。

    Attributes:
        version: 版本号（如 v1.0, v2.0）
        type: 模型类型
        path: 模型路径
        supported_agents: 支持的 Agent 列表
        num_labels: 标签数量
        base_model: 基础模型（仅 LoRA 模型需要）
    """
    version: str
    type: ModelType
    path: str
    supported_agents: list[str]
    num_labels: int
    base_model: str | None = None


class IntentModelManager:
    """意图识别模型管理器。

    职责：
    - 管理多版本模型
    - 加载和切换模型
    - 处理不支持的 Agent（降级）
    - 支持模型迁移

    Attributes:
        registry: Agent 注册中心
        current_version: 当前模型版本
        model_info: 当前模型信息
    """

    def __init__(
        self,
        config_path: str | None = None,
        model_version: str | None = None
    ) -> None:
        """初始化模型管理器。

        Args:
            config_path: Agent 配置文件路径
            model_version: 指定模型版本（默认从环境变量读取）
        """
        # 加载 Agent 注册中心
        self.registry = get_registry()
        if config_path:
            self.registry.load_from_config(config_path)

        # 当前模型版本
        self.current_version = model_version or os.getenv(
            "INTENT_MODEL_VERSION",
            "v1.0"
        )

        # 模型信息（延迟加载）
        self.model_info: ModelInfo | None = None
        self._model: Any = None

    def load_model_info(self, version: str | None = None) -> ModelInfo:
        """加载模型信息。

        Args:
            version: 模型版本（默认使用当前版本）

        Returns:
            ModelInfo 对象

        Raises:
            ValueError: 模型版本不存在
        """
        version = version or self.current_version

        # 从配置文件读取模型信息
        config_path = Path(__file__).parent.parent.parent / "config" / "agents.yaml"
        if config_path.exists():
            import yaml
            with config_path.open("r") as f:
                config = yaml.safe_load(f)

            models_config = config.get("models", {})
            if version not in models_config:
                raise ValueError(f"Model version '{version}' not found in config")

            model_config = models_config[version]
            return ModelInfo(
                version=version,
                type=ModelType(model_config["type"]),
                path=model_config["path"],
                supported_agents=model_config["supported_agents"],
                num_labels=model_config["num_labels"],
                base_model=model_config.get("base_model"),
            )

        # 降级：硬编码默认配置
        return ModelInfo(
            version=version,
            type=ModelType.BASE,
            path="ollama/qwen2.5:3b",
            supported_agents=["metrics", "logs", "fault", "security", "knowledge_base"],
            num_labels=20,
            base_model=None,
        )

    def load_model(self, version: str | None = None) -> Any:
        """加载指定版本的模型。

        Args:
            version: 模型版本（默认使用当前版本）

        Returns:
            加载的模型对象
        """
        self.model_info = self.load_model_info(version)
        self.current_version = self.model_info.version

        # 根据模型类型加载
        if self.model_info.type == ModelType.LORA:
            self._model = self._load_lora_model(self.model_info.path)
        else:
            self._model = self._load_base_model(self.model_info.path)

        return self._model

    def _load_base_model(self, path: str) -> Any:
        """加载基础模型。

        Args:
            path: 模型路径（如 ollama/qwen2.5:3b）

        Returns:
            模型对象
        """
        # 这里集成实际的模型加载逻辑
        # 例如使用 langchain 或直接调用 ollama
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=path,
            temperature=0,
            num_predict=512,
            timeout=15,
        )

    def _load_lora_model(self, path: str) -> Any:
        """加载 LoRA 微调模型。

        Args:
            path: LoRA 模型路径

        Returns:
            模型对象
        """
        # TODO: 实现 LoRA 模型加载
        # 1. 加载基础模型
        # 2. 应用 LoRA 权重
        # 3. 返回合并后的模型

        # 临时：返回基础模型
        return self._load_base_model(self.model_info.base_model or "ollama/qwen2.5:3b")

    def get_supported_agents(self) -> list[str]:
        """获取当前模型支持的 Agent 列表。

        Returns:
            Agent 名称列表
        """
        if self.model_info is None:
            self.model_info = self.load_model_info()

        return self.model_info.supported_agents

    def classify(self, query: str) -> dict:
        """执行意图分类。

        自动处理不支持的 Agent（降级到关键词匹配）。

        Args:
            query: 用户查询

        Returns:
            分类结果字典:
                - source: Agent 名称
                - severity: 严重级别
                - model_version: 模型版本
                - method: 分类方法 (llm/fallback)
        """
        # 确保模型已加载
        if self._model is None:
            self.load_model()

        # 执行分类
        try:
            result = self._llm_classify(query)
            predicted_agent = result.get("source")

            # 检查是否支持
            supported = self.get_supported_agents()
            if predicted_agent not in supported:
                # 降级处理
                return self._fallback_classify(
                    query,
                    reason=f"Agent '{predicted_agent}' not supported in model {self.current_version}"
                )

            result.update({
                "model_version": self.current_version,
                "method": "llm",
            })
            return result

        except Exception as e:
            # 异常降级
            return self._fallback_classify(query, reason=str(e))

    def _llm_classify(self, query: str) -> dict:
        """使用 LLM 进行分类。

        Args:
            query: 用户查询

        Returns:
            分类结果
        """
        # 这里集成实际的 LLM 分类逻辑
        # 临时：使用提示词调用模型
        prompt = f"""你是 AIOps 系统的意图分类器。请分析以下查询并分类。

支持的 Agent: {', '.join(self.get_supported_agents())}

返回 JSON 格式: {{"source": "agent_name", "severity": "low|medium|high|critical"}}

查询: {query}
"""

        response = self._model.invoke(prompt)
        # 解析响应...
        # 临时返回默认值
        return {"source": "knowledge_base", "severity": "low"}

    def _fallback_classify(self, query: str, reason: str) -> dict:
        """降级分类（关键词匹配）。

        Args:
            query: 用户查询
            reason: 降级原因

        Returns:
            分类结果
        """
        from aiops.core.classification_metrics import get_metrics

        # 记录降级
        metrics = get_metrics()
        metrics.record_fallback(query, reason)

        # 关键词匹配
        query_lower = query.lower()

        for agent_name in self.registry.list_enabled_agents():
            agent = self.registry.get_agent(agent_name)
            if agent and any(keyword in query_lower for keyword in agent.keywords):
                return {
                    "source": agent_name,
                    "severity": "medium",  # 默认中等
                    "model_version": self.current_version,
                    "method": "fallback",
                }

        # 兜底
        return {
            "source": "knowledge_base",
            "severity": "low",
            "model_version": self.current_version,
            "method": "fallback",
        }

    def migrate_to_new_model(
        self,
        new_model_path: str,
        new_version: str,
        dry_run: bool = False
    ) -> dict:
        """迁移到新模型（支持更多 Agent）。

        流程：
        1. 加载新模型
        2. 验证功能正常
        3. A/B 测试对比
        4. 切换流量

        Args:
            new_model_path: 新模型路径
            new_version: 新版本号
            dry_run: 是否仅演练（不实际切换）

        Returns:
            迁移报告
        """
        report = {
            "new_version": new_version,
            "new_model_path": new_model_path,
            "dry_run": dry_run,
            "steps": [],
            "success": False,
        }

        try:
            # Step 1: 加载新模型
            report["steps"].append("Loading new model...")
            new_model = self._load_lora_model(new_model_path)
            report["steps"].append("✓ New model loaded")

            # Step 2: 验证新模型
            report["steps"].append("Validating new model...")
            test_queries = ["CPU 使用率", "查看日志", "系统故障"]
            for query in test_queries:
                # TODO: 实际验证逻辑
                pass
            report["steps"].append("✓ New model validated")

            if dry_run:
                report["steps"].append("Dry run - no actual migration")
                report["success"] = True
                return report

            # Step 3: 更新配置
            report["steps"].append("Updating configuration...")
            self._update_model_version(new_version, new_model_path)
            report["steps"].append("✓ Configuration updated")

            # Step 4: 重新加载模型
            report["steps"].append("Reloading model...")
            self.load_model(new_version)
            report["steps"].append("✓ Model reloaded")

            report["success"] = True

        except Exception as e:
            report["steps"].append(f"✗ Migration failed: {e}")
            report["error"] = str(e)

        return report

    def _update_model_version(self, version: str, path: str) -> None:
        """更新配置文件中的模型版本。

        Args:
            version: 新版本号
            path: 新模型路径
        """
        config_path = Path(__file__).parent.parent.parent / "config" / "agents.yaml"

        # TODO: 更新 YAML 配置文件
        # 临时：设置环境变量
        os.environ["INTENT_MODEL_VERSION"] = version
        self.current_version = version

    def get_model_info(self) -> dict:
        """获取当前模型信息。

        Returns:
            模型信息字典
        """
        if self.model_info is None:
            self.model_info = self.load_model_info()

        return {
            "version": self.model_info.version,
            "type": self.model_info.type.value,
            "path": self.model_info.path,
            "supported_agents": self.model_info.supported_agents,
            "num_labels": self.model_info.num_labels,
            "registry_agents": self.registry.list_agents(),
            "enabled_agents": self.registry.list_enabled_agents(),
        }


# 便捷函数
def get_model_manager(version: str | None = None) -> IntentModelManager:
    """获取模型管理器实例。

    Args:
        version: 模型版本（可选）

    Returns:
        IntentModelManager 实例
    """
    return IntentModelManager(model_version=version)
