"use client";

import { useState } from "react";

/**
 * Keeps the values of a form in one object.
 *
 *   const form = useFormState({ name: "", email: "" });
 *   <input value={form.values.name} onChange={(e) => form.setField("name", e.target.value)} />
 */
export function useFormState<T>(initialValues: T) {
  const [values, setValues] = useState<T>(initialValues);

  function setField<K extends keyof T>(name: K, value: T[K]) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  return { values, setField, setValues };
}
