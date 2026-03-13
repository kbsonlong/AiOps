import unittest

from aiops.exceptions import AgentException, AIOpsException, ConfigException, SkillException, WorkflowException


class TestExceptionsStage1Task2(unittest.TestCase):
    def test_exception_inheritance(self) -> None:
        exc = AIOpsException(message="internal", safe_message="safe", error_code="code")
        self.assertIsInstance(exc, Exception)
        self.assertEqual(exc.safe_message, "safe")
        self.assertEqual(exc.error_code, "code")

        self.assertIsInstance(ConfigException("x"), AIOpsException)
        self.assertIsInstance(WorkflowException("x"), AIOpsException)
        self.assertIsInstance(SkillException("x"), AIOpsException)
        self.assertIsInstance(AgentException("x"), AIOpsException)

    def test_safe_message_defaults(self) -> None:
        self.assertEqual(ConfigException("x").safe_message, "配置错误")
        self.assertEqual(WorkflowException("x").safe_message, "工作流执行失败")
        self.assertEqual(SkillException("x").safe_message, "技能处理失败")
        self.assertEqual(AgentException("x").safe_message, "代理执行失败")


if __name__ == "__main__":
    unittest.main(verbosity=2)

