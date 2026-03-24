"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const themeOrder = ["system", "light", "dark"] as const;

type ThemeName = (typeof themeOrder)[number];

function nextTheme(theme: string | undefined): ThemeName {
  const current = themeOrder.includes(theme as ThemeName)
    ? (theme as ThemeName)
    : "system";
  const index = themeOrder.indexOf(current);
  return themeOrder[(index + 1) % themeOrder.length];
}

function themeLabel(theme: string | undefined): string {
  switch (theme) {
    case "light":
      return "Light";
    case "dark":
      return "Dark";
    default:
      return "System";
  }
}

export function ModeToggle() {
  const { resolvedTheme, setTheme, theme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const activeTheme = theme ?? "system";

  useEffect(() => {
    const timeout = window.setTimeout(() => setMounted(true), 0);
    return () => window.clearTimeout(timeout);
  }, []);

  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            onClick={() => setTheme(nextTheme(activeTheme))}
            size="icon-sm"
            type="button"
            variant="outline"
          />
        }
      >
        {mounted && resolvedTheme === "dark" ? <Moon /> : <Sun />}
        <span className="sr-only">Toggle theme</span>
      </TooltipTrigger>
      <TooltipContent>
        Theme: {themeLabel(activeTheme)}. Click to switch to{" "}
        {themeLabel(nextTheme(activeTheme)).toLowerCase()}.
      </TooltipContent>
    </Tooltip>
  );
}
