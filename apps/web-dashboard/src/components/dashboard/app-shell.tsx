"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";
import type { ReactNode } from "react";

import { ModeToggle } from "@/components/mode-toggle";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const navItems = [
  { href: "/", label: "Overview" },
  { href: "/assistant", label: "Assistant" },
  { href: "/devices", label: "Devices" },
  { href: "/automations/auto-light", label: "Auto-light" },
  { href: "/audit", label: "Audit" },
];

export function AppShell({
  title,
  description,
  subtitle,
  onLogout,
  children,
}: {
  title: string;
  description: string;
  subtitle?: string;
  onLogout: () => void;
  children: ReactNode;
}) {
  const pathname = usePathname();

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 md:px-6 lg:px-8">
        <header className="rounded-3xl border bg-card p-6 shadow-sm">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-3">
              <Badge variant="secondary" className="rounded-full px-3 py-1">
                Alice Dashboard
              </Badge>
              <div>
                <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
                <p className="mt-1 text-sm text-muted-foreground">{description}</p>
              </div>
              <nav className="flex flex-wrap gap-2">
                {navItems.map((item) => {
                  const active =
                    pathname === item.href ||
                    (item.href !== "/" && pathname.startsWith(item.href));

                  return (
                    <Link key={item.href} href={item.href}>
                      <Button
                        type="button"
                        size="sm"
                        variant={active ? "default" : "outline"}
                      >
                        {item.label}
                      </Button>
                    </Link>
                  );
                })}
              </nav>
            </div>

            <div className="flex flex-col items-start gap-3 lg:items-end">
              {subtitle ? (
                <div className="text-sm text-muted-foreground">{subtitle}</div>
              ) : null}
              <div className="flex items-center gap-2">
                <ModeToggle />
                <Button variant="outline" onClick={onLogout} type="button">
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </Button>
              </div>
            </div>
          </div>
        </header>

        {children}
      </div>
    </main>
  );
}
