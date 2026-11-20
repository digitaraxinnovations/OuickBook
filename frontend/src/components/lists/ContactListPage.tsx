"use client";

import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ContactForm } from "@/components/forms/ContactForm";
import { Button } from "@/components/ui/Button";
import { Column, DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useLoad } from "@/hooks/useLoad";
import { useQueryFlag } from "@/hooks/useQueryFlag";
import { ResourceService } from "@/services/resource.service";
import { ContactInput } from "@/types/inputs";
import { Contact, PaymentTerm } from "@/types/models";

interface ContactListPageProps<T extends Contact> {
  title: string;
  subtitle: string;
  itemName: string;
  service: ResourceService<T, ContactInput>;
  extraColumns?: Column<T>[];
  /** Customers: show the payment terms field on the form. */
  terms?: PaymentTerm[];
  /** When set, clicking a row opens this page instead of the edit form. */
  detailHref?: (row: T) => string;
  /** Vendors: show the 1099 fields on the form. */
  vendorFields?: boolean;
}

/** Shared page for Customers and Vendors: a table plus a create/edit form. */
export function ContactListPage<T extends Contact>({
  title,
  subtitle,
  itemName,
  service,
  extraColumns = [],
  terms,
  detailHref,
  vendorFields,
}: ContactListPageProps<T>) {
  const router = useRouter();
  const contacts = useLoad(() => service.list());
  const [editing, setEditing] = useState<T | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const openFromMenu = useQueryFlag("new");

  useEffect(() => {
    if (openFromMenu) {
      setFormOpen(true);
    }
  }, [openFromMenu]);

  function openNew() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(contact: T) {
    if (detailHref) {
      router.push(detailHref(contact));
      return;
    }
    setEditing(contact);
    setFormOpen(true);
  }

  async function save(input: ContactInput) {
    if (editing) {
      await service.update(editing.id, input);
    } else {
      await service.create(input);
    }
    setFormOpen(false);
    contacts.reload();
  }

  const columns: Column<T>[] = [
    {
      header: "Name",
      render: (row) => (
        <div>
          <div className="font-medium text-gray-900">{row.display_name}</div>
          {row.company_name && <div className="text-xs text-gray-500">{row.company_name}</div>}
        </div>
      ),
    },
    { header: "Email", render: (row) => row.email },
    { header: "Phone", render: (row) => row.phone },
    ...extraColumns,
    { header: "Status", render: (row) => (row.is_active ? "Active" : <span className="text-gray-400">Inactive</span>) },
  ];

  return (
    <div>
      <PageHeader
        title={title}
        subtitle={subtitle}
        actions={
          <Button onClick={openNew}>
            <Plus size={16} /> New {itemName.toLowerCase()}
          </Button>
        }
      />
      <ErrorMessage message={contacts.error} />
      {contacts.loading ? (
        <Loading />
      ) : (
        <DataTable rows={contacts.data || []} rowKey={(row) => row.id} columns={columns} onRowClick={openEdit} />
      )}
      <Modal title={editing ? "Edit " + itemName.toLowerCase() : "New " + itemName.toLowerCase()} open={formOpen} onClose={() => setFormOpen(false)}>
        <ContactForm key={editing ? editing.id : "new"} initial={editing} terms={terms} vendorFields={vendorFields} onSave={save} onCancel={() => setFormOpen(false)} />
      </Modal>
    </div>
  );
}
