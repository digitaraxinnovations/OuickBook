import { formatDate, formatMoney } from "@/lib/format";
import { ReportResult } from "@/types/models";

interface ReportViewProps {
  report: ReportResult;
  companyName: string;
  currency?: string;
}

/** Draws any report from the API, because every report has the same shape. */
export function ReportView({ report, companyName, currency }: ReportViewProps) {
  const period = report.start_date
    ? formatDate(report.start_date) + " - " + formatDate(report.end_date)
    : "As of " + formatDate(report.end_date);

  return (
    <div className="mx-auto max-w-3xl rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
      <div className="mb-8 text-center">
        <div className="text-sm text-gray-500">{companyName}</div>
        <h2 className="text-xl font-semibold">{report.title}</h2>
        <div className="text-sm text-gray-500">{period}</div>
      </div>

      {report.sections.map((section) => (
        <div key={section.title} className="mb-6">
          <div className="border-b border-gray-300 pb-1 text-sm font-semibold">{section.title}</div>
          {section.rows.length === 0 && <div className="py-2 pl-4 text-sm text-gray-400">No activity</div>}
          {section.rows.map((row) => (
            <div key={row.label} className="flex justify-between py-1.5 pl-4 text-sm">
              <span>{row.label}</span>
              <span>{formatMoney(row.amount, currency)}</span>
            </div>
          ))}
          <div className="flex justify-between border-t border-gray-200 pt-1.5 text-sm font-semibold">
            <span>Total {section.title}</span>
            <span>{formatMoney(section.total, currency)}</span>
          </div>
        </div>
      ))}

      <div className="border-t-2 border-gray-800 pt-2">
        {report.summary.map((row) => (
          <div key={row.label} className="flex justify-between py-1 text-base font-bold">
            <span>{row.label}</span>
            <span>{formatMoney(row.amount, currency)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
