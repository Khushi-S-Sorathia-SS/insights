"""
Runs generated Python code inside an isolated sandbox subprocess.
This helper is a standalone sandbox executor; the Deep Agents workflow uses DaytonaSandbox in backend/workflows/agent_planner.py.
Integrated with LangSmith for execution tracing.
"""

import base64
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict

from ..config import get_settings
from ..utils.error_handler import SandboxRuntimeError, SandboxTimeoutError
from ..utils.logger import get_logger
from ..utils.langsmith_tracer import trace_function
from .code_validator import validate_code

logger = get_logger(__name__)
settings = get_settings()


@trace_function(name="run_code_in_sandbox", tags=["sandbox", "execution"])
def run_code_in_sandbox(code: str, session_id: str, file_path: str) -> Dict[str, object]:
    """Execute sandboxed Python code safely and return output payload."""
    logger.debug(f"Executing code in sandbox for session: {session_id}")
    validate_code(code)

    with tempfile.TemporaryDirectory(prefix=f"sandbox_{session_id}_") as temp_dir:
        temp_path = Path(temp_dir)
        script_path = temp_path / "sandbox_script.py"
        script_path.write_text(code, encoding="utf-8")

        # Copy the dataset file to temp dir
        filename = Path(file_path).name
        local_file_path = temp_path / filename
        shutil.copy(file_path, local_file_path)

        start_time = time.perf_counter()
        try:
            completed = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=settings.SANDBOX_TIMEOUT,
                env=None,
            )
        except subprocess.TimeoutExpired as exc:
            raise SandboxTimeoutError(settings.SANDBOX_TIMEOUT) from exc
        finally:
            execution_time_ms = int((time.perf_counter() - start_time) * 1000)

        if completed.returncode != 0 and not completed.stdout:
            raise SandboxRuntimeError(completed.stderr.strip() or "Sandbox execution failed")

        charts = []
        for path in temp_path.glob("*.png"):
            charts.append(base64.b64encode(path.read_bytes()).decode("utf-8"))

        return {
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "charts": charts,
            "execution_time_ms": execution_time_ms,
        }
