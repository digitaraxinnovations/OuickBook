"use client";

import { Plus, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, Select, TextInput } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatDate } from "@/lib/format";
import { platformService } from "@/services";
import { Member, UserRole } from "@/types/models";

export default function UsersPage() {
  const { user } = useAuth();
  const members = useLoad(() => platformService.users());
  const invitations = useLoad(() => platformService.invitations());
  const roles = useLoad(() => platformService.roles());
  const [inviteOpen, setInviteOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<UserRole>("STANDARD");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  if (roles.loading) {
    return <Loading />;
  }
  const roleOptions = (roles.data || []).map((item) => ({ value: item.role, label: item.label }));
  const roleLabels: Record<string, string> = {};
  for (const item of roles.data || []) {
    roleLabels[item.role] = item.label.split(" - ")[0];
  }

  async function invite(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await platformService.invite(email, role);
      setInviteOpen(false);
      setMessage("Invitation sent to " + email + ". (With EMAIL_PROVIDER=log it is in Settings → Email log.)");
      setEmail("");
      invitations.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not send the invitation.");
    }
  }

  async function changeRole(member: Member, newRole: string) {
    setError(null);
    try {
      await platformService.updateUser(member.user_id, newRole as UserRole, member.is_active);
      members.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not change the role.");
    }
  }

  async function toggleActive(member: Member) {
    setError(null);
    try {
      await platformService.updateUser(member.user_id, member.role, !member.is_active);
      members.reload();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not change access.");
    }
  }

  async function cancel(id: number) {
    await platformService.cancelInvitation(id);
    invitations.reload();
  }

  return (
    <div>
      <PageHeader
        title="Users"
        subtitle="People who can sign in to this company, and what they may do."
        actions={
          <Button onClick={() => setInviteOpen(true)}>
            <Plus size={16} /> Invite a user
          </Button>
        }
      />
      <ErrorMessage message={error || members.error} />
      {message && <div className="mb-4 rounded-md bg-green-50 p-3 text-sm text-green-800">{message}</div>}
      <Card className="mb-6">
        <DataTable
          rows={members.data || []}
          rowKey={(row) => row.user_id}
          columns={[
            { header: "Name", render: (row) => <span className="font-medium">{row.full_name}</span> },
            { header: "Email", render: (row) => row.email },
            {
              header: "Role",
              render: (row) =>
                row.is_primary_admin ? (
                  "Primary admin"
                ) : (
                  <Select className="w-64!" value={row.role} onChange={(e) => changeRole(row, e.target.value)} options={roleOptions} />
                ),
            },
            { header: "Status", render: (row) => (row.is_active ? "Active" : "No access") },
            {
              header: "Access",
              align: "right",
              render: (row) =>
                row.is_primary_admin || row.user_id === user?.id ? null : (
                  <button onClick={() => toggleActive(row)} className="text-sm text-brand-700 hover:underline">
                    {row.is_active ? "Remove access" : "Give access back"}
                  </button>
                ),
            },
          ]}
        />
      </Card>
      <Card title="Pending invitations">
        <DataTable
          rows={invitations.data || []}
          rowKey={(row) => row.id}
          emptyText="No pending invitations."
          columns={[
            { header: "Email", render: (row) => row.email },
            { header: "Role", render: (row) => roleLabels[row.role] },
            { header: "Expires", render: (row) => formatDate(row.expires_at.slice(0, 10)) },
            {
              header: "Cancel",
              align: "right",
              render: (row) => (
                <button onClick={() => cancel(row.id)} className="text-gray-400 hover:text-red-600" aria-label="Cancel invitation">
                  <Trash2 size={16} />
                </button>
              ),
            },
          ]}
        />
      </Card>
      <Modal title="Invite a user" open={inviteOpen} onClose={() => setInviteOpen(false)}>
        <form onSubmit={invite} className="space-y-4">
          <Field label="Email" required>
            <TextInput type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label="Role" required>
            <Select value={role} onChange={(e) => setRole(e.target.value as UserRole)} options={roleOptions} />
          </Field>
          <p className="text-sm text-gray-500">Choose Accountant to give your accountant access.</p>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setInviteOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">Send invitation</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
