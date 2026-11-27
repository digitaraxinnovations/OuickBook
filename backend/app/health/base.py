"""
Base class for the books health check.

Each thing that can be wrong is one HealthCheck. HealthService runs them
all and scores the result. Checks only read; they never change the books.

To add a check:
  1. Write a class that inherits from HealthCheck.
  2. Add it to build_health_checks() in api/deps.py.
"""

from abc import ABC, abstractmethod
from datetime import date

from app.schemas.health import Finding, Severity


class HealthCheck(ABC):
    # Group name shown on the page.
    name: str = ""
    severity: Severity = Severity.MEDIUM

    @abstractmethod
    def run(self, company_id: int, today: date) -> list[Finding]:
        """Everything this check finds today."""

    def finding(self, key: str, title: str, detail: str, link: str) -> Finding:
        return Finding(key=key, check=self.name, severity=self.severity, title=title, detail=detail, link=link)
