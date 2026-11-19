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

export default function SignupPage() {
  const { signup } = useAuth();
  const router = useRouter();
  const form = useFormState({ full_name: "", company_name: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await signup(form.values);
      router.replace("/dashboard");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Sign up failed.");
      setSaving(false);
    }
  }

  return (
    <AuthCard title="Create your account">
      <ErrorMessage message={error} />
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Your name" required>
          <TextInput required value={form.values.full_name} onChange={(e) => form.setField("full_name", e.target.value)} />
        </Field>
        <Field label="Business name" required>
          <TextInput required value={form.values.company_name} onChange={(e) => form.setField("company_name", e.target.value)} />
        </Field>
        <Field label="Email" required>
          <TextInput type="email" required value={form.values.email} onChange={(e) => form.setField("email", e.target.value)} />
        </Field>
        <Field label="Password (at least 8 characters)" required>
          <TextInput
            type="password"
            required
            minLength={8}
            maxLength={72}
            value={form.values.password}
            onChange={(e) => form.setField("password", e.target.value)}
          />
        </Field>
        <Button type="submit" disabled={saving} className="w-full">
          {saving ? "Creating account..." : "Create account"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-gray-600">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-brand-700 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthCard>
  );
}
