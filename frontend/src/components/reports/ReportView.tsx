import Link from "next/link";
import { formatDate, formatMoney, toNumber } from "@/lib/format";
import { ColumnKind, ReportResult, ReportRow } from "@/types/models";

interface ReportViewProps {
  report: ReportResult;
  companyName: string;
  currency?: string;
  /** Link for a row that has an account (drill down to its transactions). */
  accountLink?: (accountId: number) => string;
}

function formatValue(value: string | null | undefined, kind: ColumnKind, currency?: string): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (kind === "percent") {
    return toNumber(value).toFixed(2) + "%";
  }
  if (kind === "number") {
    return String(toNumber(value));
  }
  return formatMoney(value, currency);
}

/**
 * Draws any report from the API, because every report has the same shape:
 * sections of rows with a total, plus summary lines. Multi-column reports
 * (by month, comparisons) and detail reports (with date, number, name...)
 * use the same table.
 */
export function ReportView({ report, companyName, currency, accountLink }: ReportViewProps) {
  const period = report.start_date ? formatDate(report.start_date) + " - " + formatDate(report.end_date) : "As of " + formatDate(report.end_date);
  const valueHeadings = report.columns.length > 0 ? report.columns : [""];
  const kinds: ColumnKind[] = report.columns.length > 0 ? report.column_kinds : ["money"];
  const textColumns = report.text_columns;
  const isWide = valueHeadings.length + textColumns.length > 3;
  // Detail reports start with their text columns (date, type...) instead of a label column.
  const isDetail = textColumns.length > 0;
  const columnCount = (isDetail ? textColumns.length : 1) + valueHeadings.length;

  function rowValues(row: ReportRow): (string | null)[] {
    return report.columns.length > 0 ? row.values : [row.amount];
  }

  function valueCells(values: (string | null)[], bold: boolean) {
    return values.map((value, index) => (
      <td key={index} className={"whitespace-nowrap px-2 py-1.5 text-right " + (bold ? "font-semibold" : "") + (toNumber(value) < 0 ? " text-red-700" : "")}>
        {formatValue(value, kinds[index] || "money", currency)}
      </td>
    ));
  }

  /** The label cell of a total line: one cell, or spread over the text columns of a detail report. */
  function labelCell(text: string, className: string) {
    return (
      <td colSpan={isDetail ? textColumns.length : 1} className={className}>
        {text}
      </td>
    );
  }

  function rowLabel(row: ReportRow) {
    if (row.account_id && accountLink && textColumns.length === 0) {
      return (
        <Link href={accountLink(row.account_id)} className="text-brand-700 hover:underline">
          {row.label}
        </Link>
      );
    }
    return row.label;
  }

  return (
    <div className={"mx-auto overflow-x-auto rounded-lg border border-gray-200 bg-white p-8 shadow-sm " + (isWide ? "max-w-none" : "max-w-3xl")}>
      <div className="mb-6 text-center">
        <div className="text-sm text-gray-500">{companyName}</div>
        <h2 className="text-xl font-semibold">{report.title}</h2>
        <div className="text-sm text-gray-500">
          {period}
          {report.basis === "cash" ? " · Cash basis" : ""}
        </div>
      </div>

      <table className="w-full text-sm">
        {(report.columns.length > 0 || textColumns.length > 0) && (
          <thead className="border-b-2 border-gray-300 text-xs uppercase text-gray-500">
            <tr>
              {!isDetail && <th className="py-2 text-left"></th>}
              {textColumns.map((heading) => (
                <th key={heading} className="whitespace-nowrap px-2 py-2 text-left">
                  {heading}
                </th>
              ))}
              {valueHeadings.map((heading) => (
                <th key={heading} className="whitespace-nowrap px-2 py-2 text-right">
                  {heading || "Amount"}
                </th>
              ))}
            </tr>
          </thead>
        )}
        {report.sections.map((section) => (
          <tbody key={section.title}>
            <tr>
              <td colSpan={columnCount} className="border-b border-gray-300 pt-4 pb-1 font-semibold">
                {section.title}
              </td>
            </tr>
            {section.rows.length === 0 && (
              <tr>
                <td colSpan={columnCount} className="py-2 pl-4 text-gray-400">
                  No activity
                </td>
              </tr>
            )}
            {section.rows.map((row, index) => (
              <tr key={index} className="hover:bg-gray-50">
                {!isDetail && <td className="py-1.5 pl-4 pr-2">{rowLabel(row)}</td>}
                {textColumns.map((heading, cellIndex) => (
                  <td key={heading} className="whitespace-nowrap px-2 py-1.5 text-gray-700">
                    {row.cells[cellIndex] || ""}
                  </td>
                ))}
                {valueCells(rowValues(row), false)}
              </tr>
            ))}
            <tr className="border-t border-gray-200">
              {labelCell("Total " + section.title, "py-1.5 font-semibold")}
              {valueCells(report.columns.length > 0 ? section.totals : [section.total], true)}
            </tr>
          </tbody>
        ))}
        {report.summary.length > 0 && (
          <tbody className="border-t-2 border-gray-800">
            {report.summary.map((row) => (
              <tr key={row.label} className="text-base">
                {labelCell(row.label, "py-1.5 font-bold")}
                {valueCells(rowValues(row), true)}
              </tr>
            ))}
          </tbody>
        )}
      </table>
      {report.notes.map((note) => (
        <p key={note} className="mt-4 text-sm text-gray-500">
          {note}
        </p>
      ))}
    </div>
  );
}
