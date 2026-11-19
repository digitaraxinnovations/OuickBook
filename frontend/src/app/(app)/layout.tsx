import { ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";

/** Every page inside the (app) folder gets the sidebar and top bar. */
export default function SignedInLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
