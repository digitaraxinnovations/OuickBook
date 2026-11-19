"use client";

import { Printer } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ReportView } from "@/components/reports/ReportView";
import { Button } from "@/components/ui/Button";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { firstDayOfYearString, todayString } from "@/lib/format";
import { reportService } from "@/services";

export default function ReportPage() {
  const params = useParams<{ key: string }>();
  const { company } = useAuth();
  const [startDate, setStartDate] = useState(firstDayOfYearString());
  const [endDate, setEndDate] = useState(todayString());

  const report = useLoad(
    () => reportService.runReport(params.key, startDate, endDate),
    [params.key, startDate, endDate],
  );
  const showStartDate = report.data ? report.data.start_date !== null : true;

  return (
    <div>
      <PageHeader
        title={report.data?.title || "Report"}
        actions={
          <Button variant="secondary" onClick={() => window.print()}>
            <Printer size={16} /> Print
          </Button>
        }
      />
      <div className="no-print mb-6 flex flex-wrap items-end gap-4">
        {showStartDate && (
          <div className="w-44">
            <Field label="From">
              <TextInput type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </Field>
          </div>
        )}
        <div className="w-44">
          <Field label={showStartDate ? "To" : "As of"}>
            <TextInput type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </Field>
        </div>
      </div>
      <ErrorMessage message={report.error} />
      {report.loading && <Loading />}
      {!report.loading && report.data && (
        <ReportView report={report.data} companyName={company?.name || ""} currency={company?.currency} />
      )}
    </div>
  );
}
