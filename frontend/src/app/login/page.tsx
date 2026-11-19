"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { AuthCard } from "@/components/layout/AuthCard";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, TextInput } from "@/components/ui/FormFields";
import { useAuth } from "@/context/AuthContext";
import { useFormState } from "@/hooks/useFormState";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const form = useFormState({ email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await login(form.values);
      router.replace("/dashboard");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Sign in failed.");
      setSaving(false);
    }
  }

  return (
    <AuthCard title="Sign in">
      <ErrorMessage message={error} />
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Email" required>
          <TextInput type="email" required value={form.values.email} onChange={(e) => form.setField("email", e.target.value)} />
        </Field>
        <Field label="Password" required>
          <TextInput type="password" required value={form.values.password} onChange={(e) => form.setField("password", e.target.value)} />
        </Field>
        <Button type="submit" disabled={saving} className="w-full">
          {saving ? "Signing in..." : "Sign in"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-gray-600">
        New here?{" "}
        <Link href="/signup" className="font-medium text-brand-700 hover:underline">
          Create an account
        </Link>
      </p>
    </AuthCard>
  );
}
