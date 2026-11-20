"use client";

import { Plus } from "lucide-react";
import { useState } from "react";
import { EmployeeForm } from "@/components/payroll/EmployeeForm";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatMoney } from "@/lib/format";
import { payrollService } from "@/services";
import { EmployeeInput } from "@/types/inputs";
import { Employee } from "@/types/models";

export default function EmployeesPage() {
  const { company } = useAuth();
  const employees = useLoad(() => payrollService.employees());
  const schedules = useLoad(() => payrollService.schedules());
  const payItems = useLoad(() => payrollService.payItems());
  const [editing, setEditing] = useState<Employee | null>(null);
  const [open, setOpen] = useState(false);

  if (schedules.loading || payItems.loading) {
    return <Loading />;
  }

  const scheduleNames: Record<number, string> = {};
  for (const schedule of schedules.data || []) {
    scheduleNames[schedule.id] = schedule.name;
  }

  async function save(input: EmployeeInput) {
    await payrollService.saveEmployee(input, editing?.id);
    setOpen(false);
    employees.reload();
  }

  function payText(employee: Employee): string {
    if (employee.pay_type === "HOURLY") {
      return formatMoney(employee.pay_rate, company?.currency) + " / hour";
    }
    return formatMoney(employee.pay_rate, company?.currency) + " / year";
  }

  return (
    <div>
      <PageHeader
        title="Employees"
        subtitle="People you pay through payroll. Contractors are vendors (Expenses → Vendors)."
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setOpen(true);
            }}
          >
            <Plus size={16} /> Add employee
          </Button>
        }
      />
      <ErrorMessage message={employees.error} />
      {employees.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={employees.data || []}
          rowKey={(row) => row.id}
          emptyText="No employees yet."
          onRowClick={(row) => {
            setEditing(row);
            setOpen(true);
          }}
          columns={[
            { header: "Name", render: (row) => <span className="font-medium">{row.display_name}</span> },
            { header: "Pay", render: (row) => payText(row) },
            { header: "Schedule", render: (row) => (row.pay_schedule_id ? scheduleNames[row.pay_schedule_id] : "") },
            { header: "Paid by", render: (row) => (row.payment_method === "CHECK" ? "Check" : "Direct deposit") },
            { header: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
          ]}
        />
      )}
      <Modal title={editing ? "Edit employee" : "New employee"} open={open} onClose={() => setOpen(false)} wide>
        <EmployeeForm
          key={editing ? editing.id : "new"}
          initial={editing}
          schedules={schedules.data || []}
          payItems={payItems.data || []}
          onSave={save}
          onCancel={() => setOpen(false)}
        />
      </Modal>
    </div>
  );
}
