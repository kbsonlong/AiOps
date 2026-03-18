"""Agent 注册中心，支持动态添加新的 Agent 类型。

此模块实现了可扩展的 Agent 管理机制：
- 配置驱动的 Agent 定义
- 动态注册/注销 Agent
- 模型输出层自动适配
- 向后兼容保证

使用示例:
    from aiops.core.agent_registry import get_registry

    registry = get_registry()

    # 查询 Agent
    metrics_def = registry.get_agent("metrics")

    # 列出所有启用的 Agent
    enabled_agents = registry.list_enabled_agents()

    # 获取分类标签总数（用于模型输出层）
    num_labels = registry.get_num_labels()
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Required, TypedDict

import yaml


Severity = Literal["low", "medium", "high", "critical"]


class AgentDefinition(TypedDict, total=False):
    """Agent 定义类型。

    Attributes:
        name: Agent 唯一标识符
        display_name: 显示名称（中文）
        description: 功能描述
        enabled: 是否启用
        keywords: 关键词列表（用于 fallback 分类）
        severity_levels: 支持的严重级别
        priority: 优先级（用于路由冲突解决，越小优先级越高）
        examples: 示例查询
    """
    name: str
    display_name: str
    description: str
    enabled: bool
    keywords: list[str]
    severity_levels: list[Severity]
    priority: int
    examples: list[str]


@dataclass(frozen=True)
class AgentInfo:
    """不可变的 Agent 信息对象。

    用于类型安全的 Agent 访问。
    """
    name: str
    display_name: str
    description: str
    enabled: bool
    keywords: tuple[str, ...]
    severity_levels: tuple[Severity, ...]
    priority: int
    examples: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict) -> "AgentInfo":
        """从字典创建 AgentInfo。

        Args:
            data: 包含 Agent 定义的字典

        Returns:
            AgentInfo 实例
        """
        return cls(
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            keywords=tuple(data.get("keywords", [])),
            severity_levels=tuple(data.get("severity_levels", ["low", "medium", "high", "critical"])),
            priority=data.get("priority", 99),
            examples=tuple(data.get("examples", [])),
        )


class AgentRegistry:
    """Agent 注册中心。

    线程安全的单例模式，用于管理所有 Agent 定义。

    支持操作：
    - 注册/注销 Agent
    - 查询 Agent 信息
    - 列出启用的 Agent
    - 获取模型输出层大小

    Attributes:
        _agents: Agent 名称到 AgentInfo 的映射
        _lock: 线程锁
    """

    _instance: "AgentRegistry | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        """初始化注册中心（单例模式）。"""
        if AgentRegistry._instance is not None:
            raise RuntimeError("Use get_instance() to get the singleton")

        self._agents: dict[str, AgentInfo] = {}
        self._lock = threading.Lock()

        # 加载默认配置
        self._load_default_agents()

    @classmethod
    def get_instance(cls) -> "AgentRegistry":
        """获取单例实例。

        Returns:
            AgentRegistry 单例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例（主要用于测试）。"""
        with cls._lock:
            cls._instance = None

    def _load_default_agents(self) -> None:
        """加载默认 Agent 定义。

        默认定义包括 5 个核心 Agent：
        - metrics: 系统指标
        - logs: 日志分析
        - fault: 故障诊断
        - security: 安全检查
        - knowledge_base: 通用知识
        """
        default_agents = {
            "metrics": {
                "name": "metrics",
                "display_name": "指标监控",
                "description": "CPU、内存、磁盘、网络等系统指标查询",
                "enabled": True,
                "keywords": ["cpu", "memory", "disk", "network", "指标", "监控", "使用率"],
                "severity_levels": ["low", "medium", "high", "critical"],
                "priority": 1,
                "examples": [
                    "CPU 使用率很高",
                    "查看内存占用",
                    "磁盘空间不足",
                    "网络流量怎么样",
                ],
            },
            "logs": {
                "name": "logs",
                "display_name": "日志分析",
                "description": "错误日志、异常堆栈、警告信息查询",
                "enabled": True,
                "keywords": ["log", "error", "exception", "warning", "日志", "错误", "异常"],
                "severity_levels": ["low", "medium", "high", "critical"],
                "priority": 2,
                "examples": [
                    "查看错误日志",
                    "有哪些异常",
                    "最近的 warning",
                    "日志报错了",
                ],
            },
            "fault": {
                "name": "fault",
                "display_name": "故障诊断",
                "description": "系统异常诊断、根因分析、故障排查",
                "enabled": True,
                "keywords": ["诊断", "根因", "异常", "崩溃", "故障", "排查"],
                "severity_levels": ["low", "medium", "high", "critical"],
                "priority": 3,
                "examples": [
                    "系统为什么崩溃",
                    "帮我分析故障",
                    "找出问题原因",
                    "服务异常了",
                ],
            },
            "security": {
                "name": "security",
                "display_name": "安全检查",
                "description": "安全漏洞、入侵检测、权限审计",
                "enabled": True,
                "keywords": ["安全", "漏洞", "入侵", "权限", "攻击", "审计"],
                "severity_levels": ["low", "medium", "high", "critical"],
                "priority": 4,
                "examples": [
                    "检查安全漏洞",
                    "有没有异常登录",
                    "权限配置检查",
                    "安全审计",
                ],
            },
            "knowledge_base": {
                "name": "knowledge_base",
                "display_name": "知识库",
                "description": "通用运维知识查询",
                "enabled": True,
                "keywords": [],
                "severity_levels": ["low", "medium", "high", "critical"],
                "priority": 99,  # 兜底
                "examples": [
                    "如何配置监控",
                    "部署文档在哪",
                    "运维手册",
                    "最佳实践",
                ],
            },
        }

        for name, definition in default_agents.items():
            self._agents[name] = AgentInfo.from_dict(definition)

    def load_from_config(self, config_path: str | Path) -> None:
        """从配置文件加载 Agent 定义。

        Args:
            config_path: YAML 配置文件路径

        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: 配置文件格式错误
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with config_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        agents_config = config.get("agents", {})

        with self._lock:
            for name, definition in agents_config.items():
                definition["name"] = name
                self._agents[name] = AgentInfo.from_dict(definition)

    def register_agent(self, agent_def: dict | AgentInfo) -> None:
        """注册新的 Agent 类型。

        Args:
            agent_def: Agent 定义（字典或 AgentInfo）

        Raises:
            ValueError: Agent 已存在
        """
        if isinstance(agent_def, dict):
            info = AgentInfo.from_dict(agent_def)
        else:
            info = agent_def

        with self._lock:
            if info.name in self._agents:
                raise ValueError(f"Agent '{info.name}' already exists")
            self._agents[info.name] = info

    def unregister_agent(self, name: str) -> None:
        """注销 Agent 类型（慎用）。

        Args:
            name: Agent 名称

        Raises:
            ValueError: Agent 不存在
        """
        with self._lock:
            if name not in self._agents:
                raise ValueError(f"Agent '{name}' not found")
            del self._agents[name]

    def get_agent(self, name: str) -> AgentInfo | None:
        """获取 Agent 定义。

        Args:
            name: Agent 名称

        Returns:
            AgentInfo 对象，不存在时返回 None
        """
        return self._agents.get(name)

    def list_agents(self) -> list[str]:
        """列出所有 Agent 名称。

        Returns:
            Agent 名称列表
        """
        return list(self._agents.keys())

    def list_enabled_agents(self) -> list[str]:
        """列出所有启用的 Agent。

        Returns:
            启用的 Agent 名称列表（按优先级排序）
        """
        with self._lock:
            enabled = [
                name for name, info in self._agents.items()
                if info.enabled
            ]
            # 按优先级排序
            enabled.sort(key=lambda n: self._agents[n].priority)
            return enabled

    def get_num_labels(self) -> int:
        """获取分类标签总数。

        用于模型输出层大小计算。
        假设每个 Agent 有 4 个 severity 级别。

        Returns:
            标签总数 (Agent 数量 × 4)
        """
        return len(self._agents) * 4

    def get_num_enabled_labels(self) -> int:
        """获取启用 Agent 的标签总数。

        Returns:
            启用 Agent 的标签总数
        """
        enabled = self.list_enabled_agents()
        return len(enabled) * 4

    def get_agent_by_priority(self, priority: int) -> AgentInfo | None:
        """根据优先级获取 Agent。

        Args:
            priority: 优先级数值

        Returns:
            匹配的 AgentInfo，不存在时返回 None
        """
        for info in self._agents.values():
            if info.priority == priority:
                return info
        return None

    def get_keywords_for_agent(self, name: str) -> list[str]:
        """获取 Agent 的关键词列表。

        Args:
            name: Agent 名称

        Returns:
            关键词列表
        """
        info = self.get_agent(name)
        return list(info.keywords) if info else []

    def is_agent_enabled(self, name: str) -> bool:
        """检查 Agent 是否启用。

        Args:
            name: Agent 名称

        Returns:
            是否启用
        """
        info = self.get_agent(name)
        return info.enabled if info else False


def get_registry() -> AgentRegistry:
    """获取 Agent 注册中心实例。

    Returns:
        AgentRegistry 单例
    """
    return AgentRegistry.get_instance()


# 导出的 Source 类型（保持向后兼容）
Source = Literal["metrics", "logs", "fault", "security", "knowledge_base"]
