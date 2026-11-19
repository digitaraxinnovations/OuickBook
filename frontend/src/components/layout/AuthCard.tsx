import { ReactNode } from "react";
import { appConfig } from "@/config/app.config";

/** Centered card used by the sign-in and sign-up pages. */
export function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-page px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-600 text-lg font-bold text-white">
            {appConfig.appName.charAt(0)}
          </div>
          <span className="text-2xl font-semibold text-gray-900">{appConfig.appName}</span>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
          <h1 className="mb-6 text-xl font-semibold text-gray-900">{title}</h1>
          {children}
        </div>
      </div>
    </div>
  );
}
