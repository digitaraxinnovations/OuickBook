"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { AuthCard } from "@/components/layout/AuthCard";
import { Button } from "@/components/ui/Button";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, TextInput } from "@/components/ui/FormFields";
import { useAuth } from "@/context/AuthContext";
import { authService, platformService } from "@/services";
import { InvitationInfo } from "@/types/models";

/** Opened from the invitation email: join the company (with a new or existing account). */
export default function AcceptInvitePage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [token, setToken] = useState("");
  const [info, setInfo] = useState<InvitationInfo | null>(null);
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fromAddress = new URLSearchParams(window.location.search).get("token") || "";
    setToken(fromAddress);
    platformService
      .invitationInfo(fromAddress)
      .then(setInfo)
      .catch((problem) => setError(problem instanceof Error ? problem.message : "This invitation is not valid."))
      .finally(() => setLoading(false));
  }, []);

  async function accept(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await authService.acceptInvitation(token, fullName, password);
      await refresh();
      router.replace("/dashboard");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not accept the invitation.");
      setSaving(false);
    }
  }

  if (loading) {
    return <Loading />;
  }

  return (
    <AuthCard title={info ? "Join " + info.company_name : "Invitation"}>
      <ErrorMessage message={error} />
      {info && (
        <form onSubmit={accept} className="space-y-4">
          <p className="text-sm text-gray-600">
            You were invited as <strong>{info.email}</strong>.{" "}
            {info.has_account ? "Enter your Ledgerly password to add this company to your account." : "Choose your name and a password."}
          </p>
          {!info.has_account && (
            <Field label="Your name" required>
              <TextInput required value={fullName} onChange={(e) => setFullName(e.target.value)} />
            </Field>
          )}
          <Field label="Password" required>
            <TextInput type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <Button type="submit" disabled={saving} className="w-full">
            {saving ? "Joining..." : "Accept invitation"}
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
