from dataclasses import dataclass, field
from typing import Any

@dataclass
class CheckResult:
    check: str
    score: int
    detail: str
    value: Any = None
    remediation: str = ''
    is_delta: bool = False

@dataclass
class FileResult:
    filepath: str
    size_bytes: int = 0
    verdict: str = 'PASS'
    total_score: int = 0
    correlations_triggered: list[str] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)

    def add_check(self, check: CheckResult):
        self.checks.append(check)