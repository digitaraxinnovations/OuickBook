"use client";

import { RefreshCw, Upload, Wand2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AddBankLineDialog } from "@/components/banking/AddBankLineDialog";
import { ImportStatementDialog } from "@/components/banking/ImportStatementDialog";
import { MatchDialog } from "@/components/banking/MatchDialog";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading, SuccessMessage } from "@/components/ui/Feedback";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatLabel, formatMoney, toNumber } from "@/lib/format";
import { accountService, bankingService, vendorService } from "@/services";
import { BankTransaction, BankTransactionStatus } from "@/types/models";

const tabs: { status: BankTransactionStatus; label: string }[] = [
  { status: "FOR_REVIEW", label: "For review" },
  { status: "ADDED", label: "Added" },
  { status: "MATCHED", label: "Matched" },
  { status: "EXCLUDED", label: "Excluded" },
];

export default function BankTransactionsPage() {
  const { company } = useAuth();
  const currency = company?.currency;
  const overview = useLoad(() => bankingService.accounts());
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const vendors = useLoad(() => vendorService.list({ active_only: true }));
  const [accountId, setAccountId] = useState<number | null>(null);
  const [status, setStatus] = useState<BankTransactionStatus>("FOR_REVIEW");
  const [importOpen, setImportOpen] = useState(false);
  const [adding, setAdding] = useState<BankTransaction | null>(null);
  const [matching, setMatching] = useState<BankTransaction | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const transactions = useLoad(
    () => (accountId ? bankingService.transactions(accountId, status) : Promise.resolve([])),
    [accountId, status],
  );

  // Open the first bank account automatically.
  useEffect(() => {
    if (accountId === null && overview.data && overview.data.length > 0) {
      setAccountId(overview.data[0].account.id);
    }
  }, [accountId, overview.data]);

  if (overview.loading || accounts.loading) {
    return <Loading />;
  }

  const current = (overview.data || []).find((item) => item.account.id === accountId);
  const categoryOptions = (accounts.data || [])
    .filter((account) => account.id !== accountId && account.system_key !== "accounts_receivable" && account.system_key !== "accounts_payable")
    .map((account) => ({ value: account.id, label: account.full_name }));
  const vendorOptions = (vendors.data || []).map((vendor) => ({ value: vendor.id, label: vendor.display_name }));

  function refresh() {
    overview.reload();
    transactions.reload();
  }

  async function run(action: () => Promise<string | void>) {
    setError(null);
    setMessage(null);
    try {
      const text = await action();
      if (text) {
        setMessage(text);
      }
      refresh();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Something went wrong.");
    }
  }

  async function applyRulesNow(id: number) {
    const result = await bankingService.applyRules(id);
    return "Rules checked " + result.count + " line(s).";
  }

  async function updateFromBank(id: number) {
    const result = await bankingService.syncFeed(id);
    return result.imported + " new line(s) from the bank feed.";
  }

  async function excludeLine(line: BankTransaction) {
    await bankingService.exclude(line.id);
  }

  async function undoLine(line: BankTransaction) {
    await bankingService.undo(line.id);
    return "Sent back to For review.";
  }

  return (
    <div>
      <PageHeader
        title="Bank transactions"
        subtitle="Review what happened in your bank and card accounts and add it to your books."
        actions={
          accountId && (
            <>
              <Button variant="secondary" onClick={() => run(() => applyRulesNow(accountId))}>
                <Wand2 size={16} /> Apply rules
              </Button>
              <Button variant="secondary" onClick={() => run(() => updateFromBank(accountId))}>
                <RefreshCw size={16} /> Update from bank
              </Button>
              <Button onClick={() => setImportOpen(true)}>
                <Upload size={16} /> Upload statement
              </Button>
            </>
          )
        }
      />
      <ErrorMessage message={error || overview.error} />
      <SuccessMessage message={message} />

      {(overview.data || []).length === 0 && (
        <p className="text-sm text-gray-500">
          No bank or credit card accounts yet. Add one in <Link href="/accounting/chart-of-accounts" className="text-brand-700 underline">Chart of accounts</Link> with
          detail type &quot;Bank&quot; or &quot;Credit Card&quot;.
        </p>
      )}

      <div className="mb-6 flex gap-4 overflow-x-auto pb-1">
        {(overview.data || []).map((item) => (
          <button
            key={item.account.id}
            onClick={() => setAccountId(item.account.id)}
            className={
              "min-w-56 rounded-lg border bg-white p-4 text-left shadow-sm " +
              (item.account.id === accountId ? "border-brand-600 ring-2 ring-brand-100" : "border-gray-200 hover:border-gray-300")
            }
          >
            <div className="text-xs font-semibold uppercase text-gray-500">{item.detail_type}</div>
            <div className="font-semibold">{item.account.name}</div>
            <div className="mt-2 text-sm text-gray-600">In books: {formatMoney(item.books_balance, currency)}</div>
            <div className="text-sm">
              {item.for_review_count > 0 ? <span className="font-semibold text-amber-700">{item.for_review_count} to review</span> : <span className="text-gray-400">Nothing to review</span>}
            </div>
            <div className="mt-1 text-xs text-gray-400">
              {item.last_reconciled ? "Reconciled to " + formatDate(item.last_reconciled) : "Never reconciled"}
            </div>
          </button>
        ))}
      </div>

      {current && (
        <>
          <div className="mb-4 flex gap-1 border-b border-gray-200">
            {tabs.map((tab) => (
              <button
                key={tab.status}
                onClick={() => setStatus(tab.status)}
                className={
                  "-mb-px border-b-2 px-4 py-2 text-sm font-medium " +
                  (status === tab.status ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-800")
                }
              >
                {tab.label}
                {tab.status === "FOR_REVIEW" && current.for_review_count > 0 ? " (" + current.for_review_count + ")" : ""}
              </button>
            ))}
          </div>
          {transactions.loading ? (
            <Loading />
          ) : (
            <DataTable
              rows={transactions.data || []}
              rowKey={(row) => row.id}
              emptyText={status === "FOR_REVIEW" ? "Nothing to review. Upload a statement to bring in new lines." : "Nothing here."}
              columns={[
                { header: "Date", render: (row) => formatDate(row.txn_date) },
                { header: "Description", render: (row) => row.description },
                {
                  header: status === "FOR_REVIEW" ? "Suggested category" : "Added as",
                  render: (row) =>
                    status === "FOR_REVIEW"
                      ? row.suggested_account?.name || <span className="text-gray-400">-</span>
                      : formatLabel(row.added_as || status),
                },
                { header: "Spent", align: "right", render: (row) => (toNumber(row.amount) < 0 ? formatMoney(-toNumber(row.amount), currency) : "") },
                { header: "Received", align: "right", render: (row) => (toNumber(row.amount) > 0 ? formatMoney(row.amount, currency) : "") },
                {
                  header: "",
                  align: "right",
                  render: (row) =>
                    status === "FOR_REVIEW" ? (
                      <span className="flex justify-end gap-2">
                        <Button variant="ghost" className="px-2! py-1!" onClick={() => setMatching(row)}>
                          Match
                        </Button>
                        <Button variant="ghost" className="px-2! py-1!" onClick={() => run(() => excludeLine(row))}>
                          Exclude
                        </Button>
                        <Button className="px-3! py-1!" onClick={() => setAdding(row)}>
                          Add
                        </Button>
                      </span>
                    ) : (
                      <Button variant="ghost" className="px-2! py-1!" onClick={() => run(() => undoLine(row))}>
                        Undo
                      </Button>
                    ),
                },
              ]}
            />
          )}
        </>
      )}

      {current && importOpen && (
        <ImportStatementDialog
          open
          accountId={current.account.id}
          accountName={current.account.name}
          onClose={() => setImportOpen(false)}
          onImported={(result) => {
            setImportOpen(false);
            setStatus("FOR_REVIEW");
            setMessage(
              result.imported + " new line(s) imported, " + result.duplicates + " already imported" +
                (result.auto_added ? ", " + result.auto_added + " added by rules" : "") + ".",
            );
            refresh();
          }}
        />
      )}
      {adding && (
        <AddBankLineDialog
          transaction={adding}
          categoryOptions={categoryOptions}
          vendorOptions={vendorOptions}
          currency={currency}
          onClose={() => setAdding(null)}
          onDone={() => {
            setAdding(null);
            refresh();
          }}
        />
      )}
      {matching && (
        <MatchDialog
          transaction={matching}
          currency={currency}
          onClose={() => setMatching(null)}
          onDone={() => {
            setMatching(null);
            refresh();
          }}
        />
      )}
    </div>
  );
}
