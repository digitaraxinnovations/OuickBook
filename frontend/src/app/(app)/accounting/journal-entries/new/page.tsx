"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import {
  emptyJournalLine,
  JournalLinesEditor,
  journalLinesToInput,
  JournalLineState,
  journalTotals,
} from "@/components/forms/JournalLinesEditor";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, TextInput } from "@/components/ui/FormFields";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { todayString } from "@/lib/format";
import { accountService, journalService } from "@/services";

export default function NewJournalEntryPage() {
  const { company } = useAuth();
  const router = useRouter();
  const accounts = useLoad(() => accountService.list({ active_only: true }));

  const [entryDate, setEntryDate] = useState(todayString());
  const [memo, setMemo] = useState("");
  const [lines, setLines] = useState<JournalLineState[]>([emptyJournalLine(), emptyJournalLine()]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (accounts.loading) {
    return <Loading />;
  }
  const accountOptions = (accounts.data || []).map((account) => ({ value: account.id, label: account.full_name }));

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await journalService.create({ entry_date: entryDate, memo: memo, lines: journalLinesToInput(lines) });
      router.push("/accounting/journal-entries");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the journal entry.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <PageHeader title="New journal entry" subtitle="Total debits must equal total credits." />
      <ErrorMessage message={error} />

      <Card>
        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <Field label="Date" required>
            <TextInput type="date" required value={entryDate} onChange={(e) => setEntryDate(e.target.value)} />
          </Field>
          <div className="md:col-span-2">
            <Field label="Memo">
              <TextInput value={memo} onChange={(e) => setMemo(e.target.value)} />
            </Field>
          </div>
        </div>
        <JournalLinesEditor lines={lines} onChange={setLines} accountOptions={accountOptions} currency={company?.currency} />
      </Card>

      <div className="mt-6 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={() => router.back()}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving || !journalTotals(lines).isBalanced}>
          {saving ? "Saving..." : "Save journal entry"}
        </Button>
      </div>
    </form>
  );
}
