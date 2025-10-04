from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import List, Optional

from .logging import get_logger


@dataclass
class CommandResult:
    command: List[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


logger = get_logger(__name__)


def run_command(command: List[str], cwd: Optional[str] = None, timeout: Optional[int] = None) -> CommandResult:
    logger.info("run_command", command=command, cwd=cwd)
    proc = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        text=True,
        shell=False,
    )
    result = CommandResult(command=command, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
    logger.info("run_command_completed", command=command, returncode=proc.returncode)
    return result
