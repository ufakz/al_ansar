"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  AlertTriangle,
  FileText,
  Scale,
  Users,
  Kanban,
  PlusCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/ThemeToggle";

const navItems = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/crises", label: "Crises", icon: AlertTriangle },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/legal", label: "Legal", icon: Scale },
  { href: "/ansar", label: "Ansar", icon: Users },
  { href: "/tasks", label: "Tasks", icon: Kanban },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="relative flex min-h-screen">
      {/* Atmospheric grid */}
      <div className="pointer-events-none fixed inset-0 app-grid opacity-60" aria-hidden />

      <aside className="glass-panel fixed inset-y-0 left-0 z-30 flex w-60 flex-col">
        <div className="flex h-[4.25rem] items-center gap-3 border-b border-border/80 px-5">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-primary font-display text-lg font-semibold text-primary-foreground shadow-lg shadow-primary/20">
            <span className="relative z-10">ا</span>
            <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-white/20 to-transparent" />
          </div>
          <div>
            <p className="font-display text-base font-semibold tracking-tight">Al-Ansar</p>
            <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              Crisis Operations
            </p>
          </div>
        </div>

        <nav className="flex-1 space-y-0.5 p-3">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-200",
                  active
                    ? "nav-active-glow bg-primary/10 font-medium text-primary"
                    : "text-muted-foreground hover:bg-secondary/80 hover:text-foreground"
                )}
              >
                <Icon className={cn("h-4 w-4", active && "text-primary")} />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="space-y-2 border-t border-border/80 p-3">
          <Link
            href="/report"
            className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-accent/10 hover:text-accent"
          >
            <PlusCircle className="h-4 w-4" />
            Report incident
          </Link>
          <div className="flex items-center justify-between px-1 pt-1">
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Theme</p>
            <ThemeToggle />
          </div>
        </div>
      </aside>

      <div className="flex flex-1 flex-col pl-60">
        <main className="page-enter flex-1 p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
