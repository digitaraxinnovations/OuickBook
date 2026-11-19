import type { Metadata } from "next";
import { ReactNode } from "react";
import { appConfig } from "@/config/app.config";
import { AuthProvider } from "@/context/AuthContext";
import "./globals.css";

export const metadata: Metadata = {
  title: appConfig.appName,
  description: "Simple accounting for small businesses",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
