"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { todayString } from "@/lib/format";
import { reportService } from "@/services";
import { ReportSchedule, SavedReport } from "@/types/models";

interface ScheduleDialogProps {
  saved: SavedReport;
  schedule: ReportSchedule | null;
  onClose: () => void;
  onSaved: () => void;
}

/** Email a saved report every day, week or month (sent by the daily job). */
export function ScheduleDialog({ saved, schedule, onClose, onSaved }: ScheduleDialogProps) {
  const [frequency, setFrequency] = useState<string>(schedule ? schedule.frequency : "WEEKLY");
  const [nextDate, setNextDate] = useState(schedule ? schedule.next_send_date : todayString());
  const [recipients, setRecipients] = useState(schedule ? schedule.recipients.join(", ") : "");
  const [fileFormat, setFileFormat] = useState<string>(schedule ? schedule.file_format : "pdf");
  const [isActive, setIsActive] = useState(schedule ? schedule.is_active : true);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const addresses = recipients
      .split(/[,;\s]+/)
      .map((address) => address.trim())
      .filter((address) => address);
    try {
      await reportService.saveSchedule(
        {
          saved_report_id: saved.id,
          frequency: frequency as ReportSchedule["frequency"],
          next_send_date: nextDate,
          recipients: addresses,
          file_format: fileFormat as ReportSchedule["file_format"],
          is_active: isActive,
        },
        schedule?.id,
      );
      onSaved();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not save the schedule.");
    }
  }

  async function remove() {
    if (schedule && window.confirm("Stop emailing this report?")) {
      await reportService.deleteSchedule(schedule.id);
      onSaved();
    }
  }

  return (
    <Modal title={"Email " + saved.name} open={true} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <ErrorMessage message={error} />
        <div className="grid grid-cols-3 gap-4">
          <Field label="Send">
            <Select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              options={[
                { value: "DAILY", label: "Every day" },
                { value: "WEEKLY", label: "Every week" },
                { value: "MONTHLY", label: "Every month" },
              ]}
            />
          </Field>
          <Field label="Next send date" required>
            <TextInput type="date" required value={nextDate} onChange={(e) => setNextDate(e.target.value)} />
          </Field>
          <Field label="As">
            <Select
              value={fileFormat}
              onChange={(e) => setFileFormat(e.target.value)}
              options={[
                { value: "pdf", label: "PDF" },
                { value: "xlsx", label: "Excel" },
                { value: "csv", label: "CSV" },
              ]}
            />
          </Field>
        </div>
        <Field label="To (email addresses, separated by commas)" required>
          <TextInput required value={recipients} onChange={(e) => setRecipients(e.target.value)} />
        </Field>
        {schedule && (
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Active
          </label>
        )}
        <p className="text-xs text-gray-500">
          Emails go out with the daily job. With EMAIL_PROVIDER=log they are recorded in Settings → Email log instead of being sent.
        </p>
        <div className="flex justify-between gap-2">
          <div>
            {schedule && (
              <Button type="button" variant="danger" onClick={remove}>
                Stop emailing
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit">Save</Button>
          </div>
        </div>
      </form>
    </Modal>
  );
}
