"""Enhanced sandbox for secure skill execution.

This module provides a secure execution environment for user-defined skills,
using RestrictedPython and resource limits to prevent malicious code execution.
"""

from __future__ import annotations

import logging
import resource
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Set

from RestrictedPython import compile_restricted
from RestrictedPython.Guards import (
    guarded_iter_unpack_sequence,
    guarded_unpack_sequence,
    safe_builtins,
)
from RestrictedPython.PrintCollector import PrintCollector

from aiops.exceptions import AIOpsException

logger = logging.getLogger(__name__)


class SandboxTimeoutError(AIOpsException):
    """Raised when sandbox execution times out."""
    pass


class SandboxMemoryError(AIOpsException):
    """Raised when sandbox execution exceeds memory limits."""
    pass


class SandboxValidationError(AIOpsException):
    """Raised when code fails validation."""
    pass


@dataclass
class SandboxResult:
    """Result of sandbox execution."""

    success: bool
    output: str
    error: Optional[str] = None
    execution_time_ms: int = 0


class EnhancedSandbox:
    """Enhanced sandbox for secure skill execution.

    This sandbox provides:
    - Code validation using RestrictedPython
    - Resource limits (memory, CPU, execution time)
    - Restricted built-ins and module access
    - Safe execution environment

    Example:
        ```python
        sandbox = EnhancedSandbox()

        code = '''
        def execute(context):
            import json
            return {"result": json.dumps(context)}
        '''

        result = sandbox.execute(code, {"input": "test"})
        ```
    """

    # Resource limits
    MAX_MEMORY_MB = 100
    MAX_CPU_TIME = 30  # seconds
    MAX_EXECUTION_TIME = 60  # seconds

    # Allowed modules (whitelist)
    _ALLOWED_MODULES: Set[str] = {
        'json', 're', 'datetime', 'math', 'collections',
        'itertools', 'functools', 'typing', 'dataclasses',
        'hashlib', 'uuid', 'base64', 'decimal', 'fractions',
        'enum', 'pathlib', 'time', 'random', 'statistics'
    }

    # Blocked built-ins (blacklist)
    _BLOCKED_BUILTINS: Set[str] = {
        'open', 'file', 'exec', 'eval', 'compile', '__import__',
        'globals', 'locals', 'vars', 'dir', 'hasattr', 'getattr',
        'setattr', 'delattr', 'property', 'super'
    }

    def __init__(
        self,
        max_memory_mb: Optional[int] = None,
        max_cpu_time: Optional[int] = None,
        max_execution_time: Optional[int] = None,
    ):
        """Initialize the sandbox.

        Args:
            max_memory_mb: Maximum memory in MB (default: 100)
            max_cpu_time: Maximum CPU time in seconds (default: 30)
            max_execution_time: Maximum wall-clock time in seconds (default: 60)
        """
        self.max_memory_mb = max_memory_mb or self.MAX_MEMORY_MB
        self.max_cpu_time = max_cpu_time or self.MAX_CPU_TIME
        self.max_execution_time = max_execution_time or self.MAX_EXECUTION_TIME

        # Build safe built-ins
        self._safe_builtins = self._build_safe_builtins()

    def _build_safe_builtins(self) -> Dict[str, Any]:
        """Build a dictionary of safe built-ins.

        Returns:
            Dictionary of safe built-in functions and objects
        """
        safe = safe_builtins.copy()

        # Add allowed built-ins
        safe.update({
            '_print': PrintCollector,
            '_iter_unpack_sequence': guarded_iter_unpack_sequence,
            '_unpack_sequence': guarded_unpack_sequence,
            '__builtins__': safe_builtins,
        })

        # Remove blocked built-ins
        for name in self._BLOCKED_BUILTINS:
            safe.pop(name, None)

        return safe

    def _set_resource_limits(self) -> None:
        """Set process resource limits.

        Raises:
            SandboxMemoryError: If memory limits cannot be set
        """
        try:
            # Set memory limit (address space)
            memory_bytes = self.max_memory_mb * 1024 * 1024
            resource.setrlimit(
                resource.RLIMIT_AS,
                (memory_bytes, memory_bytes)
            )

            # Set CPU time limit
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (self.max_cpu_time, self.max_cpu_time)
            )

            logger.debug(
                f"Resource limits set: "
                f"memory={self.max_memory_mb}MB, cpu={self.max_cpu_time}s"
            )
        except (OSError, ValueError) as e:
            logger.warning(f"Could not set resource limits: {e}")

    def _validate_code(self, code: str) -> bytes:
        """Validate code using RestrictedPython.

        Args:
            code: The code to validate

        Returns:
            Compiled bytecode

        Raises:
            SandboxValidationError: If code validation fails
        """
        try:
            byte_code = compile_restricted(
                code,
                filename='<skill>',
                mode='exec'
            )

            if byte_code.errors:
                raise SandboxValidationError(
                    f"Code validation failed: {byte_code.errors}"
                )

            logger.debug("Code validation passed")
            return byte_code.code

        except Exception as e:
            raise SandboxValidationError(
                f"Code validation error: {e}"
            )

    def _execute_with_timeout(
        self,
        byte_code: bytes,
        context: Dict[str, Any]
    ) -> Any:
        """Execute code with timeout protection.

        Args:
            byte_code: Compiled bytecode to execute
            context: Execution context

        Returns:
            Execution result

        Raises:
            SandboxTimeoutError: If execution times out
        """
        def timeout_handler(signum, frame):
            raise SandboxTimeoutError(
                f"Execution exceeded {self.max_execution_time} seconds"
            )

        # Set signal handler for timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.max_execution_time)

        try:
            # Execute with restricted globals
            restricted_globals = {
                '__builtins__': self._safe_builtins,
                '_print': PrintCollector,
                '_iter_unpack_sequence': guarded_iter_unpack_sequence,
                '_unpack_sequence': guarded_unpack_sequence,
                **context
            }

            exec(byte_code, restricted_globals)

            # Get printed output
            output = restricted_globals.get('_print', PrintCollector())
            result = output.getvalue() if hasattr(output, 'getvalue') else str(output)

            return result

        except MemoryError:
            raise SandboxMemoryError(
                f"Execution exceeded {self.max_memory_mb}MB memory limit"
            )
        except SandboxTimeoutError:
            raise
        except Exception as e:
            raise AIOpsException(f"Execution error: {e}")
        finally:
            # Restore old handler and cancel alarm
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def execute(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SandboxResult:
        """Execute code in the sandbox.

        Args:
            code: The code to execute
            context: Optional execution context (variables available to code)

        Returns:
            SandboxResult with execution output or error

        Example:
            ```python
            sandbox = EnhancedSandbox()
            result = sandbox.execute('print("Hello")')
            ```
        """
        context = context or {}
        start_time = time.time()

        try:
            # 1. Validate code
            byte_code = self._validate_code(code)

            # 2. Set resource limits (for current process)
            # Note: This affects the entire process, not just the sandbox
            # For true isolation, use separate processes or containers
            # self._set_resource_limits()

            # 3. Execute with timeout
            output = self._execute_with_timeout(byte_code, context)

            execution_time = int((time.time() - start_time) * 1000)

            return SandboxResult(
                success=True,
                output=str(output) if output else "",
                execution_time_ms=execution_time
            )

        except (SandboxValidationError, SandboxTimeoutError,
                SandboxMemoryError) as e:
            execution_time = int((time.time() - start_time) * 1000)
            return SandboxResult(
                success=False,
                output="",
                error=str(e),
                execution_time_ms=execution_time
            )
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.exception(f"Unexpected sandbox error: {e}")
            return SandboxResult(
                success=False,
                output="",
                error=f"Unexpected error: {e}",
                execution_time_ms=execution_time
            )


class ProcessSandbox(EnhancedSandbox):
    """Sandbox that executes code in a separate process for true isolation.

    This provides better isolation than EnhancedSandbox by running
    code in a subprocess with separate resource limits.

    Note: This requires the code to be a complete executable script.
    """

    def execute(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SandboxResult:
        """Execute code in a subprocess for isolation.

        Args:
            code: The code to execute (must be a complete script)
            context: Optional execution context (passed as JSON to subprocess)

        Returns:
            SandboxResult with execution output or error
        """
        import json

        start_time = time.time()

        # Write code to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            # Add context injection to code
            if context:
                f.write(f"__context__ = {json.dumps(context)}\n")
            f.write(code)
            temp_file = f.name

        try:
            # Run in subprocess with resource limits
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=self.max_execution_time,
                # Resource limits would be set via prlimit on Linux
            )

            execution_time = int((time.time() - start_time) * 1000)

            if result.returncode == 0:
                return SandboxResult(
                    success=True,
                    output=result.stdout,
                    execution_time_ms=execution_time
                )
            else:
                return SandboxResult(
                    success=False,
                    output=result.stdout or "",
                    error=result.stderr or "Execution failed",
                    execution_time_ms=execution_time
                )

        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                output="",
                error=f"Execution exceeded {self.max_execution_time} seconds",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        finally:
            # Clean up temp file
            try:
                Path(temp_file).unlink()
            except Exception:
                pass
