"use client";

import { Printer } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading, SuccessMessage } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { openBlobInNewTab } from "@/lib/files";
import { formatDate, formatMoney } from "@/lib/format";
import { checkService } from "@/services";
import { CheckToPrint } from "@/types/models";

function keyOf(check: CheckToPrint): string {
  return check.source_type + "-" + check.source_id;
}

/** Checks saved with "print later" are numbered and printed here. */
export default function PrintChecksPage() {
  const { company } = useAuth();
  const waiting = useLoad(() => checkService.toPrint());
  const [bankAccountId, setBankAccountId] = useState("");
  const [firstNumber, setFirstNumber] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const checks = waiting.data || [];

  // Bank accounts that have checks waiting.
  const banks: { value: number; label: string }[] = [];
  for (const check of checks) {
    if (!banks.find((bank) => bank.value === check.bank_account.id)) {
      banks.push({ value: check.bank_account.id, label: check.bank_account.name });
    }
  }

  // Pick the first bank automatically and look up its next check number.
  useEffect(() => {
    if (!bankAccountId && banks.length > 0) {
      setBankAccountId(String(banks[0].value));
    }
  }, [bankAccountId, banks]);

  useEffect(() => {
    if (!bankAccountId) {
      return;
    }
    checkService.nextNumber(Number(bankAccountId)).then((result) => setFirstNumber(String(result.next_check_number)));
  }, [bankAccountId]);

  if (waiting.loading) {
    return <Loading />;
  }

  const forBank = checks.filter((check) => String(check.bank_account.id) === bankAccountId);

  function toggle(check: CheckToPrint) {
    const key = keyOf(check);
    setSelected(selected.includes(key) ? selected.filter((item) => item !== key) : [...selected, key]);
  }

  async function print() {
    setError(null);
    setMessage(null);
    const items = forBank
      .filter((check) => selected.includes(keyOf(check)))
      .map((check) => ({ source_type: check.source_type, source_id: check.source_id }));
    try {
      openBlobInNewTab(await checkService.print(Number(bankAccountId), Number(firstNumber), items));
      setMessage(items.length + " check(s) numbered from " + firstNumber + ". Print the PDF that opened.");
      setSelected([]);
      waiting.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not print.");
    }
  }

  return (
    <div>
      <PageHeader title="Print checks" subtitle="Checks and bill payments saved with “print later”." />
      <ErrorMessage message={error} />
      <SuccessMessage message={message} />
      <Card>
        {checks.length === 0 ? (
          <p className="text-sm text-gray-500">No checks are waiting to be printed.</p>
        ) : (
          <>
            <div className="mb-4 grid gap-4 md:grid-cols-3">
              <Field label="Bank account">
                <Select value={bankAccountId} onChange={(e) => setBankAccountId(e.target.value)} options={banks} />
              </Field>
              <Field label="Starting check no.">
                <TextInput type="number" min="1" value={firstNumber} onChange={(e) => setFirstNumber(e.target.value)} />
              </Field>
            </div>
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <tr>
                  <th className="w-8 py-2">
                    <input
                      type="checkbox"
                      checked={forBank.length > 0 && selected.length === forBank.length}
                      onChange={(e) => setSelected(e.target.checked ? forBank.map(keyOf) : [])}
                    />
                  </th>
                  <th className="py-2">Date</th>
                  <th className="py-2">Payee</th>
                  <th className="py-2">Type</th>
                  <th className="py-2 text-right">Amount</th>
                </tr>
              </thead>
              <tbody>
                {forBank.map((check) => (
                  <tr key={keyOf(check)} className="border-b border-gray-100">
                    <td className="py-2">
                      <input type="checkbox" checked={selected.includes(keyOf(check))} onChange={() => toggle(check)} />
                    </td>
                    <td className="py-2">{formatDate(check.check_date)}</td>
                    <td className="py-2">{check.payee}</td>
                    <td className="py-2">{check.source_type === "EXPENSE" ? "Check" : "Bill payment"}</td>
                    <td className="py-2 text-right">{formatMoney(check.amount, company?.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-4 flex justify-end">
              <Button onClick={print} disabled={selected.length === 0 || !firstNumber}>
                <Printer size={16} /> Print {selected.length} check(s)
              </Button>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
