"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useLoad } from "@/hooks/useLoad";
import { reportService } from "@/services";
import { HealthFinding, HealthSeverity } from "@/types/models";

const groups: { severity: HealthSeverity; title: string; color: string }[] = [
  { severity: "HIGH", title: "Look at these first", color: "bg-red-100 text-red-700" },
  { severity: "MEDIUM", title: "Tidy up soon", color: "bg-amber-100 text-amber-800" },
  { severity: "LOW", title: "When you have time", color: "bg-gray-100 text-gray-600" },
];

function scoreColor(score: number): string {
  if (score >= 90) {
    return "text-brand-700";
  }
  return score >= 70 ? "text-amber-700" : "text-red-600";
}

interface FindingRowProps {
  finding: HealthFinding;
  color: string;
  onToggle: (finding: HealthFinding) => void;
}

function FindingRow({ finding, color, onToggle }: FindingRowProps) {
  return (
    <li className={"flex flex-wrap items-center gap-3 px-5 py-3 " + (finding.dismissed ? "opacity-60" : "")}>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium text-gray-900">
          <span className={"mr-2 rounded-full px-2 py-0.5 text-xs font-semibold " + color}>{finding.check}</span>
          {finding.title}
        </div>
        <div className="mt-1 text-sm text-gray-500">{finding.detail}</div>
      </div>
      <Link href={finding.link} className="text-sm font-medium text-brand-700 hover:underline">
        Open
      </Link>
      <Button variant="secondary" onClick={() => onToggle(finding)}>
        {finding.dismissed ? "Bring back" : "This is fine"}
      </Button>
    </li>
  );
}

export default function HealthCheckPage() {
  const health = useLoad(() => reportService.getHealthCheck());
  const [showDismissed, setShowDismissed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!health.data) {
    return health.loading ? <Loading /> : <ErrorMessage message={health.error} />;
  }
  const findings = health.data.findings;
  const open = findings.filter((finding) => !finding.dismissed);
  const dismissed = findings.length - open.length;
  const shown = showDismissed ? findings : open;

  async function toggle(finding: HealthFinding) {
    setError(null);
    try {
      if (finding.dismissed) {
        await reportService.restoreFinding(finding.key);
      } else {
        await reportService.dismissFinding(finding.key);
      }
      health.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save that.");
    }
  }

  return (
    <div>
      <PageHeader title="Books health check" subtitle="Things worth a look before month end. Nothing here changes your books." />
      <ErrorMessage message={error || health.error} />

      <Card className="mb-6">
        <div className="flex flex-wrap items-center gap-6">
          <div className={"text-4xl font-semibold " + scoreColor(health.data.score)}>
            {health.data.score}
            <span className="text-lg text-gray-400"> / 100</span>
          </div>
          <div className="text-sm text-gray-600">
            {open.length === 0 ? "No problems found." : open.length + " thing(s) to look at."}
            {dismissed > 0 && (
              <label className="mt-1 flex items-center gap-2">
                <input type="checkbox" checked={showDismissed} onChange={(e) => setShowDismissed(e.target.checked)} />
                Show the {dismissed} marked as fine
              </label>
            )}
          </div>
        </div>
      </Card>

      {groups.map((group) => {
        const rows = shown.filter((finding) => finding.severity === group.severity);
        if (rows.length === 0) {
          return null;
        }
        return (
          <Card key={group.severity} title={group.title} className="mb-6">
            <ul className="-m-5 divide-y divide-gray-100">
              {rows.map((finding) => (
                <FindingRow key={finding.key} finding={finding} color={group.color} onToggle={toggle} />
              ))}
            </ul>
          </Card>
        );
      })}
    </div>
  );
}
