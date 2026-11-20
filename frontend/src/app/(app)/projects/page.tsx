"use client";

import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ProjectForm, projectStatusOptions } from "@/components/projects/ProjectForm";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useLoad } from "@/hooks/useLoad";
import { useQueryFlag } from "@/hooks/useQueryFlag";
import { formatDate } from "@/lib/format";
import { customerService, trackingService } from "@/services";

export default function ProjectsPage() {
  const router = useRouter();
  const projects = useLoad(() => trackingService.projects());
  const customers = useLoad(() => customerService.list({ active_only: true }));
  const [open, setOpen] = useState(false);
  const openFromMenu = useQueryFlag("new");

  useEffect(() => {
    if (openFromMenu) {
      setOpen(true);
    }
  }, [openFromMenu]);

  if (customers.loading) {
    return <Loading />;
  }
  const customerNames: Record<number, string> = {};
  for (const customer of customers.data || []) {
    customerNames[customer.id] = customer.display_name;
  }
  const statusLabels: Record<string, string> = {};
  for (const option of projectStatusOptions) {
    statusLabels[option.value] = option.label;
  }

  return (
    <div>
      <PageHeader
        title="Projects"
        subtitle="Jobs for a customer. Put the project on invoices, bills, expenses and time to see if it makes money."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus size={16} /> New project
          </Button>
        }
      />
      <ErrorMessage message={projects.error} />
      {projects.loading ? (
        <Loading />
      ) : (
        <DataTable
          rows={projects.data || []}
          rowKey={(row) => row.id}
          emptyText="No projects yet."
          onRowClick={(row) => router.push("/projects/" + row.id)}
          columns={[
            { header: "Project", render: (row) => <span className="font-medium">{row.name}</span> },
            { header: "Customer", render: (row) => customerNames[row.customer_id] },
            { header: "Dates", render: (row) => (row.start_date ? formatDate(row.start_date) : "") + (row.end_date ? " - " + formatDate(row.end_date) : "") },
            { header: "Status", render: (row) => statusLabels[row.status] },
          ]}
        />
      )}
      <Modal title="New project" open={open} onClose={() => setOpen(false)}>
        {open && (
          <ProjectForm
            initial={null}
            customers={customers.data || []}
            onSaved={(project) => router.push("/projects/" + project.id)}
            onCancel={() => setOpen(false)}
          />
        )}
      </Modal>
    </div>
  );
}
