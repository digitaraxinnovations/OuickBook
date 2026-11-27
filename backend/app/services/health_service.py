"""
Books health check: run every check, score the result, and remember which
findings the user said are fine. The books themselves are never changed.
"""

from datetime import date

from app.core.config import Settings
from app.health.base import HealthCheck
from app.models import HealthDismissal
from app.repositories.health_repository import HealthDismissalRepository
from app.schemas.health import Finding, HealthReport, Severity
from app.services.base import BaseService

SEVERITY_ORDER = [Severity.HIGH, Severity.MEDIUM, Severity.LOW]


class HealthService(BaseService):
    def __init__(self, session, settings: Settings, repository: HealthDismissalRepository, checks: list[HealthCheck]):
        super().__init__(session)
        self.settings = settings
        self.repository = repository
        self.checks = checks

    def report(self, company_id: int, today: date | None = None) -> HealthReport:
        today = today or date.today()
        dismissed = {row.finding_key for row in self.repository.list_all(company_id)}
        findings = []
        for check in self.checks:
            for finding in check.run(company_id, today):
                finding.dismissed = finding.key in dismissed
                findings.append(finding)
        findings.sort(key=lambda item: (SEVERITY_ORDER.index(item.severity), item.check, item.title))
        return HealthReport(score=self.score(findings), findings=findings)

    def score(self, findings: list[Finding]) -> int:
        """100 minus points per finding. One busy check can only take so many."""
        points = {
            Severity.HIGH: self.settings.health_points_high,
            Severity.MEDIUM: self.settings.health_points_medium,
            Severity.LOW: self.settings.health_points_low,
        }
        lost: dict[str, int] = {}
        for finding in findings:
            if not finding.dismissed:
                lost[finding.check] = lost.get(finding.check, 0) + points[finding.severity]
        total = sum(min(value, self.settings.health_max_points_per_check) for value in lost.values())
        return max(100 - total, 0)

    def dismiss(self, company_id: int, key: str) -> None:
        if self.repository.get_by_key(company_id, key) is None:
            self.repository.add(HealthDismissal(company_id=company_id, finding_key=key))
            self.commit()

    def restore(self, company_id: int, key: str) -> None:
        row = self.repository.get_by_key(company_id, key)
        if row is not None:
            self.repository.delete(row)
            self.commit()
