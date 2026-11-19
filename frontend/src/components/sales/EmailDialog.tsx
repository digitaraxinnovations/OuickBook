"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, TextArea, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { EmailInput } from "@/types/inputs";

interface EmailDialogProps {
  title: string;
  open: boolean;
  defaultTo: string | null;
  onClose: () => void;
  onSend: (input: EmailInput) => Promise<void>;
}

/** Asks who to send a document to. Empty subject/message = the standard text. */
export function EmailDialog({ title, open, defaultTo, onClose, onSend }: EmailDialogProps) {
  const [to, setTo] = useState(defaultTo || "");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      await onSend({ to: to, subject: subject, message: message });
      onClose();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not send.");
    } finally {
      setSending(false);
    }
  }

  return (
    <Modal title={title} open={open} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <ErrorMessage message={error} />
        <Field label="To" required>
          <TextInput type="email" required value={to} onChange={(e) => setTo(e.target.value)} />
        </Field>
        <Field label="Subject (leave empty for the standard subject)">
          <TextInput value={subject} onChange={(e) => setSubject(e.target.value)} />
        </Field>
        <Field label="Message (leave empty for the standard message)">
          <TextArea rows={5} value={message} onChange={(e) => setMessage(e.target.value)} />
        </Field>
        <p className="text-xs text-gray-500">The PDF is attached automatically.</p>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={sending}>
            {sending ? "Sending..." : "Send"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
