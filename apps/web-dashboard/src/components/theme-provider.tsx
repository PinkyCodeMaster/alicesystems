"use client";

import * as React from "react";

type ThemeName = "light" | "dark" | "system";
type ResolvedThemeName = "light" | "dark";

type ThemeProviderProps = {
  children: React.ReactNode;
  attribute?: "class";
  defaultTheme?: ThemeName;
  disableTransitionOnChange?: boolean;
  enableSystem?: boolean;
};

type ThemeContextValue = {
  theme: ThemeName;
  resolvedTheme: ResolvedThemeName;
  setTheme: (theme: ThemeName) => void;
};

const THEME_STORAGE_KEY = "alice.dashboard.theme";
const ThemeContext = React.createContext<ThemeContextValue | null>(null);

function getSystemTheme(): ResolvedThemeName {
  if (typeof window === "undefined") {
    return "light";
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function getStoredTheme(defaultTheme: ThemeName): ThemeName {
  if (typeof window === "undefined") {
    return defaultTheme;
  }

  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored;
  }

  return defaultTheme;
}

function getResolvedTheme(
  theme: ThemeName,
  enableSystem: boolean,
): ResolvedThemeName {
  if (theme === "system") {
    return enableSystem ? getSystemTheme() : "light";
  }

  return theme;
}

export function ThemeProvider({
  children,
  defaultTheme = "system",
  disableTransitionOnChange = true,
  enableSystem = true,
}: ThemeProviderProps) {
  const [theme, setThemeState] = React.useState<ThemeName>(defaultTheme);
  const [resolvedTheme, setResolvedTheme] =
    React.useState<ResolvedThemeName>("light");

  React.useEffect(() => {
    const nextTheme = getStoredTheme(defaultTheme);
    setThemeState(nextTheme);
    setResolvedTheme(getResolvedTheme(nextTheme, enableSystem));
  }, [defaultTheme, enableSystem]);

  React.useEffect(() => {
    if (!enableSystem || theme !== "system") {
      return;
    }

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setResolvedTheme(getSystemTheme());
    mediaQuery.addEventListener("change", onChange);
    onChange();

    return () => mediaQuery.removeEventListener("change", onChange);
  }, [enableSystem, theme]);

  React.useEffect(() => {
    const root = document.documentElement;
    const nextResolved = getResolvedTheme(theme, enableSystem);
    const previousTransition = root.style.transition;

    if (disableTransitionOnChange) {
      root.style.transition = "none";
    }

    root.classList.remove("light", "dark");
    root.classList.add(nextResolved);
    setResolvedTheme(nextResolved);

    if (disableTransitionOnChange) {
      window.setTimeout(() => {
        root.style.transition = previousTransition;
      }, 0);
    }
  }, [disableTransitionOnChange, enableSystem, theme]);

  const setTheme = React.useCallback((nextTheme: ThemeName) => {
    setThemeState(nextTheme);
    window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
  }, []);

  const value = React.useMemo(
    () => ({
      theme,
      resolvedTheme,
      setTheme,
    }),
    [resolvedTheme, setTheme, theme],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const value = React.useContext(ThemeContext);
  if (value === null) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return value;
}
