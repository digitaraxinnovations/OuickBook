"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useLoad } from "@/hooks/useLoad";
import { reportService } from "@/services";

export default function ReportsPage() {
  const reports = useLoad(() => reportService.listReports());

  return (
    <div>
      <PageHeader title="Reports" subtitle="See how your business is doing." />
      <ErrorMessage message={reports.error} />
      {reports.loading ? (
        <Loading />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {(reports.data || []).map((report) => (
            <Link
              key={report.key}
              href={"/reports/" + report.key}
              className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-5 shadow-sm hover:border-brand-500"
            >
              <div>
                <div className="font-semibold text-gray-900">{report.title}</div>
                <div className="mt-1 text-sm text-gray-500">{report.description}</div>
              </div>
              <ChevronRight className="text-gray-400" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
