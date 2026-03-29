import { FormEvent } from "react";

import { ModeToggle } from "@/components/mode-toggle";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { HealthCheckState } from "@/lib/alice-client";

function healthVariant(status: HealthCheckState["status"]) {
  if (status === "reachable") return "default";
  if (status === "checking") return "secondary";
  return "destructive";
}

export function LoginCard({
  apiBaseUrl,
  assistantBaseUrl,
  loginEmail,
  loginPassword,
  loginError,
  isLoggingIn,
  hubHealth,
  assistantHealth,
  onSubmit,
  onEmailChange,
  onPasswordChange,
}: {
  apiBaseUrl: string;
  assistantBaseUrl: string;
  loginEmail: string;
  loginPassword: string;
  loginError: string | null;
  isLoggingIn: boolean;
  hubHealth: HealthCheckState;
  assistantHealth: HealthCheckState;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
}) {
  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex min-h-screen max-w-6xl items-center justify-center px-4">
        <Card className="w-full max-w-md rounded-3xl border shadow-lg">
          <CardHeader className="space-y-3">
            <div className="flex items-center justify-between">
              <Badge variant="secondary" className="rounded-full px-3 py-1">
                Alice Web
              </Badge>
              <ModeToggle />
            </div>
            <div>
              <CardTitle className="text-2xl">Sign in to this home</CardTitle>
              <CardDescription className="pt-1">
                Use the local account created on this hub. Alice Web is the advanced surface for
                devices, automations, audit, and assistant review.
              </CardDescription>
              <div className="space-y-2 pt-3 text-xs text-muted-foreground">
                <div>Hub target: {apiBaseUrl}</div>
                <div>Assistant target: {assistantBaseUrl}</div>
              </div>
              <div className="space-y-2 pt-3">
                <div className="flex items-center justify-between gap-3">
                  <Badge variant={healthVariant(hubHealth.status)}>
                    Hub: {hubHealth.status}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {hubHealth.message}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <Badge variant={healthVariant(assistantHealth.status)}>
                    Assistant: {assistantHealth.status}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {assistantHealth.message}
                  </span>
                </div>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  autoComplete="email"
                  value={loginEmail}
                  onChange={(event) => onEmailChange(event.target.value)}
                  placeholder="you@home.local"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={loginPassword}
                  onChange={(event) => onPasswordChange(event.target.value)}
                  placeholder="Your password"
                />
              </div>

              {loginError ? (
                <Alert variant="destructive">
                  <AlertTitle>Login failed</AlertTitle>
                  <AlertDescription>{loginError}</AlertDescription>
                </Alert>
              ) : null}

              <Button className="w-full" disabled={isLoggingIn} type="submit">
                {isLoggingIn ? "Signing in..." : "Sign in"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
