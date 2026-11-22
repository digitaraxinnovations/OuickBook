"use client";

import { Download, Upload } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { ErrorMessage } from "@/components/ui/Feedback";
import { saveBlob } from "@/lib/files";
import { platformService } from "@/services";
import { ImportResult } from "@/types/models";

const LISTS = [
  { name: "customers", title: "Customers", columns: "Name, Company, Email, Phone, Address, Notes" },
  { name: "vendors", title: "Vendors", columns: "Name, Company, Email, Phone, Address, Notes" },
  { name: "accounts", title: "Chart of accounts", columns: "Number, Name, Type (ASSET, LIABILITY, EQUITY, INCOME, EXPENSE), Detail type, Description, Parent" },
  { name: "journal-entries", title: "Transactions (journal entries)", columns: "Entry no, Date, Account, Debit, Credit, Description, Memo - rows with the same Entry no are one entry" },
  { name: "products", title: "Products and services", columns: "Name, SKU, Type, Description, Sales price, Purchase cost, Taxable, Category, Quantity on hand, Reorder point, Active" },
];

function ListCard({ name, title, columns }: { name: string; title: string; columns: string }) {
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function exportList() {
    setError(null);
    try {
      saveBlob(await platformService.exportData(name), name + ".csv");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not export.");
    }
  }

  async function importFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await platformService.importData(name, await file.text()));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not import.");
    }
    setBusy(false);
  }

  return (
    <Card title={title}>
      <p className="mb-3 text-xs text-gray-500">Columns: {columns}</p>
      <div className="flex flex-wrap gap-2">
        <button onClick={exportList} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50">
          <Download size={14} /> Export CSV
        </button>
        <label className="flex cursor-pointer items-center gap-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50">
          <Upload size={14} /> {busy ? "Importing..." : "Import CSV"}
          <input type="file" accept=".csv,text/csv" className="hidden" onChange={importFile} disabled={busy} />
        </label>
      </div>
      <div className="mt-3">
        <ErrorMessage message={error} />
        {result && result.errors.length === 0 && (
          <div className="rounded-md bg-green-50 p-2 text-sm text-green-800">
            Added {result.created}
            {result.updated ? ", updated " + result.updated : ""}.
          </div>
        )}
        {result && result.errors.length > 0 && (
          <div className="rounded-md bg-red-50 p-2 text-sm text-red-800">
            <div className="font-medium">Nothing was imported. Fix these and try again:</div>
            <ul className="list-disc pl-5">
              {result.errors.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Card>
  );
}

export default function ImportExportPage() {
  return (
    <div>
      <p className="mb-4 text-sm text-gray-600">
        Move lists in and out as CSV files (Excel opens and saves them). Imports are all or nothing. Products and services can also be imported on the{" "}
        <Link href="/sales/products" className="text-brand-700 hover:underline">
          Products and services
        </Link>{" "}
        page; reports export from each report.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {LISTS.map((item) => (
          <ListCard key={item.name} name={item.name} title={item.title} columns={item.columns} />
        ))}
      </div>
    </div>
  );
}
