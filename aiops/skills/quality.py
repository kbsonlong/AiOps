from __future__ import annotations

import re
from typing import Dict, List

from aiops.skills.user_models import QualityScore


class SkillQualityEvaluator:
    """Evaluate skill quality for admission gate."""

    def evaluate(self, content: str) -> QualityScore:
        scores = {
            "completeness": self._check_completeness(content),
            "clarity": self._check_clarity(content),
            "structure": self._check_structure(content),
            "safety": self._check_safety_indicators(content),
            "reusability": self._check_reusability(content),
        }
        weights = {
            "completeness": 0.3,
            "clarity": 0.25,
            "structure": 0.2,
            "safety": 0.15,
            "reusability": 0.1,
        }
        overall = sum(scores[key] * weights[key] for key in scores)
        return QualityScore(
            overall=overall,
            category_scores=scores,
            recommendations=self._generate_recommendations(scores),
        )

    def _check_completeness(self, content: str) -> float:
        required_sections = [
            r"^##?\s+概述",
            r"^##?\s+输入参数",
            r"^##?\s+执行步骤",
            r"^##?\s+输出格式",
            r"^##?\s+注意事项",
        ]
        found = sum(1 for pattern in required_sections if re.search(pattern, content, re.MULTILINE))
        return found / len(required_sections)

    def _check_clarity(self, content: str) -> float:
        code_blocks = re.findall(r"```[a-z]*\n(.*?)\n```", content, re.DOTALL)
        explained_blocks = sum(1 for block in code_blocks if len(block.strip()) > 0)
        has_examples = "示例" in content or "example" in content.lower()
        score = (explained_blocks / max(len(code_blocks), 1)) * 0.7 + (0.3 if has_examples else 0.0)
        return min(1.0, score)

    def _check_structure(self, content: str) -> float:
        lines = content.splitlines()
        heading_levels = []
        for line in lines:
            if line.startswith("#"):
                level = len(line.split()[0])
                heading_levels.append(level)
        if heading_levels and max(heading_levels) > 4:
            return 0.7
        long_paragraphs = sum(1 for line in lines if len(line.strip()) > 200)
        if long_paragraphs > 3:
            return 0.8
        return 1.0

    def _check_safety_indicators(self, content: str) -> float:
        safety_indicators = [
            r"需要.*权限",
            r"谨慎执行",
            r"确认.*再执行",
            r"备份.*再操作",
            r"测试环境.*先验证",
        ]
        found = sum(1 for pattern in safety_indicators if re.search(pattern, content))
        return min(1.0, found / 3)

    def _check_reusability(self, content: str) -> float:
        has_parameters = "输入参数" in content and "默认" in content
        has_conditions = any(word in content.lower() for word in ["如果", "当", "若", "else", "if"])
        has_error_handling = any(
            word in content.lower() for word in ["错误", "异常", "失败", "error", "exception"]
        )
        indicators = [has_parameters, has_conditions, has_error_handling]
        return sum(indicators) / len(indicators)

    def _generate_recommendations(self, scores: Dict[str, float]) -> List[str]:
        recommendations: List[str] = []
        if scores.get("completeness", 0.0) < 1.0:
            recommendations.append("补齐概述/输入参数/执行步骤/输出格式/注意事项等必需章节。")
        if scores.get("clarity", 0.0) < 0.7:
            recommendations.append("为代码块补充说明，并提供示例。")
        if scores.get("safety", 0.0) < 0.7:
            recommendations.append("增加安全提示，例如备份、权限或测试环境说明。")
        if scores.get("reusability", 0.0) < 0.7:
            recommendations.append("增加参数化、条件分支或错误处理说明。")
        return recommendations
