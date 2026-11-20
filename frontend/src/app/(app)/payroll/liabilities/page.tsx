"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { payItemKindLabels } from "@/config/payroll.config";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney, todayString, toNumber } from "@/lib/format";
import { accountService, payrollService } from "@/services";
import { Account, LiabilityBalance, LiabilityPayment } from "@/types/models";

function PayLiabilityForm({ balance, banks, onSaved, onCancel }: { balance: LiabilityBalance; banks: Account[]; onSaved: () => void; onCancel: () => void }) {
  const [amount, setAmount] = useState(balance.balance);
  const [paymentDate, setPaymentDate] = useState(todayString());
  const [bankId, setBankId] = useState(banks.length > 0 ? String(banks[0].id) : "");
  const [memo, setMemo] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await payrollService.payLiability({
        pay_item_id: balance.pay_item_id,
        payment_date: paymentDate,
        amount: amount,
        bank_account_id: Number(bankId),
        memo: memo,
      });
      onSaved();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not record the payment.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ErrorMessage message={error} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Amount" required>
          <TextInput type="number" step="0.01" min="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} />
        </Field>
        <Field label="Payment date" required>
          <TextInput type="date" required value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} />
        </Field>
      </div>
      <Field label="Pay from" required>
        <Select required value={bankId} onChange={(e) => setBankId(e.target.value)} options={banks.map((bank) => ({ value: bank.id, label: bank.full_name }))} />
      </Field>
      <Field label="Memo">
        <TextInput value={memo} onChange={(e) => setMemo(e.target.value)} placeholder="e.g. Q4 federal deposit" />
      </Field>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Record payment</Button>
      </div>
    </form>
  );
}

export default function PayrollLiabilitiesPage() {
  const { company } = useAuth();
  const currency = company?.currency;
  const balances = useLoad(() => payrollService.liabilities());
  const payments = useLoad(() => payrollService.liabilityPayments());
  const accounts = useLoad(() => accountService.list({ active_only: true }));
  const [paying, setPaying] = useState<LiabilityBalance | null>(null);

  if (balances.loading || accounts.loading) {
    return <Loading />;
  }
  const banks = (accounts.data || []).filter((account) => account.detail_type === "Bank");
  const names: Record<number, string> = {};
  let totalDue = 0;
  for (const row of balances.data || []) {
    names[row.pay_item_id] = row.name;
    totalDue += toNumber(row.balance);
  }

  function afterSave() {
    setPaying(null);
    balances.reload();
    payments.reload();
  }

  async function voidPayment(payment: LiabilityPayment) {
    if (window.confirm("Void this payment?")) {
      await payrollService.voidLiabilityPayment(payment.id);
      afterSave();
    }
  }

  return (
    <div>
      <PageHeader title="Payroll liabilities" subtitle="Deductions and taxes you have withheld or owe, until you pay them on." />
      <ErrorMessage message={balances.error} />
      <Card title={"Owed now: " + formatMoney(totalDue, currency)} className="mb-6">
        <DataTable
          rows={balances.data || []}
          rowKey={(row) => row.pay_item_id}
          emptyText="Nothing withheld yet."
          columns={[
            { header: "Pay item", render: (row) => row.name },
            { header: "Kind", render: (row) => payItemKindLabels[row.kind] },
            { header: "From payrolls", align: "right", render: (row) => formatMoney(row.accrued, currency) },
            { header: "Paid", align: "right", render: (row) => formatMoney(row.paid, currency) },
            { header: "Owed", align: "right", render: (row) => <strong>{formatMoney(row.balance, currency)}</strong> },
            {
              header: "Pay",
              align: "right",
              render: (row) =>
                toNumber(row.balance) > 0 ? (
                  <button onClick={() => setPaying(row)} className="text-sm font-medium text-brand-700 hover:underline">
                    Pay
                  </button>
                ) : null,
            },
          ]}
        />
      </Card>
      <Card title="Payments">
        <DataTable
          rows={payments.data || []}
          rowKey={(row) => row.id}
          emptyText="No liability payments yet."
          columns={[
            { header: "Date", render: (row) => formatDate(row.payment_date) },
            { header: "Pay item", render: (row) => names[row.pay_item_id] },
            { header: "From", render: (row) => row.bank_account.name },
            { header: "Memo", render: (row) => row.memo },
            { header: "Amount", align: "right", render: (row) => (row.is_void ? <span className="text-gray-400">Void</span> : formatMoney(row.amount, currency)) },
            {
              header: "Void",
              align: "right",
              render: (row) =>
                row.is_void ? null : (
                  <button onClick={() => voidPayment(row)} className="text-sm text-gray-500 hover:text-red-600">
                    Void
                  </button>
                ),
            },
          ]}
        />
      </Card>
      <Modal title={paying ? "Pay " + paying.name : ""} open={paying !== null} onClose={() => setPaying(null)}>
        {paying && <PayLiabilityForm balance={paying} banks={banks} onSaved={afterSave} onCancel={() => setPaying(null)} />}
      </Modal>
    </div>
  );
}
