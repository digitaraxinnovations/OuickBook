import Link from "next/link";
import { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

const variantClasses: Record<Variant, string> = {
  primary: "bg-brand-600 text-white hover:bg-brand-700 disabled:bg-brand-600/50",
  secondary: "bg-white text-gray-800 border border-gray-300 hover:bg-gray-50",
  danger: "bg-white text-red-600 border border-red-300 hover:bg-red-50",
  ghost: "text-brand-700 hover:bg-brand-50",
};

const baseClasses =
  "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  children: ReactNode;
}

export function Button({ variant = "primary", className = "", children, ...rest }: ButtonProps) {
  return (
    <button className={baseClasses + " " + variantClasses[variant] + " " + className} {...rest}>
      {children}
    </button>
  );
}

interface LinkButtonProps {
  href: string;
  variant?: Variant;
  children: ReactNode;
}

export function LinkButton({ href, variant = "primary", children }: LinkButtonProps) {
  return (
    <Link href={href} className={baseClasses + " " + variantClasses[variant]}>
      {children}
    </Link>
  );
}
