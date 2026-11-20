"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { useLoad } from "@/hooks/useLoad";
import { formatDate, formatMoney } from "@/lib/format";
import { bankingService } from "@/services";
import { BankTransaction } from "@/types/models";

interface MatchDialogProps {
  transaction: BankTransaction;
  currency?: string;
  onClose: () => void;
  onDone: () => void;
}

/** Link a bank line to a transaction that is already in the books (same amount, close date). */
export function MatchDialog({ transaction, currency, onClose, onDone }: MatchDialogProps) {
  const candidates = useLoad(() => bankingService.matches(transaction.id), [transaction.id]);
  const [error, setError] = useState<string | null>(null);

  async function match(journalLineId: number) {
    setError(null);
    try {
      await bankingService.match(transaction.id, journalLineId);
      onDone();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not match.");
    }
  }

  return (
    <Modal title="Find a match" open onClose={onClose}>
      <p className="mb-4 text-sm text-gray-600">
        {formatDate(transaction.txn_date)} · {transaction.description} · <strong>{formatMoney(transaction.amount, currency)}</strong>
      </p>
      <ErrorMessage message={error} />
      {candidates.loading && <Loading />}
      {!candidates.loading && (candidates.data || []).length === 0 && (
        <p className="text-sm text-gray-500">No transaction in the books has this amount within two weeks. Use Add instead.</p>
      )}
      <ul className="divide-y divide-gray-100">
        {(candidates.data || []).map((candidate) => (
          <li key={candidate.journal_line_id} className="flex items-center justify-between py-3 text-sm">
            <div>
              <div className="font-medium">{candidate.description}</div>
              <div className="text-gray-500">{formatDate(candidate.entry_date)}</div>
            </div>
            <div className="flex items-center gap-3">
              <span>{formatMoney(candidate.amount, currency)}</span>
              <Button onClick={() => match(candidate.journal_line_id)}>Match</Button>
            </div>
          </li>
        ))}
      </ul>
    </Modal>
  );
}
