"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export function TopBar() {
  const { user, company, logout } = useAuth();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <header className="no-print flex h-14 items-center justify-between border-b border-gray-200 bg-white px-6">
      <div className="text-sm font-semibold text-gray-800">{company?.name}</div>
      <div className="flex items-center gap-4 text-sm text-gray-600">
        <span>{user?.full_name}</span>
        <button onClick={handleLogout} className="flex items-center gap-1 rounded px-2 py-1 hover:bg-gray-100" title="Sign out">
          <LogOut size={16} /> Sign out
        </button>
      </div>
    </header>
  );
}
