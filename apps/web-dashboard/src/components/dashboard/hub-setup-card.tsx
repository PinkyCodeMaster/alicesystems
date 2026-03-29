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

export function HubSetupCard({
  apiBaseUrl,
  assistantBaseUrl,
  siteName,
  timezone,
  ownerEmail,
  ownerDisplayName,
  password,
  passwordConfirm,
  roomNames,
  setupError,
  isSubmitting,
  hubHealth,
  assistantHealth,
  onSubmit,
  onSiteNameChange,
  onTimezoneChange,
  onOwnerEmailChange,
  onOwnerDisplayNameChange,
  onPasswordChange,
  onPasswordConfirmChange,
  onRoomNamesChange,
}: {
  apiBaseUrl: string;
  assistantBaseUrl: string;
  siteName: string;
  timezone: string;
  ownerEmail: string;
  ownerDisplayName: string;
  password: string;
  passwordConfirm: string;
  roomNames: string;
  setupError: string | null;
  isSubmitting: boolean;
  hubHealth: HealthCheckState;
  assistantHealth: HealthCheckState;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onSiteNameChange: (value: string) => void;
  onTimezoneChange: (value: string) => void;
  onOwnerEmailChange: (value: string) => void;
  onOwnerDisplayNameChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onPasswordConfirmChange: (value: string) => void;
  onRoomNamesChange: (value: string) => void;
}) {
  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex min-h-screen max-w-6xl items-center justify-center px-4 py-8">
        <Card className="w-full max-w-2xl rounded-3xl border shadow-lg">
          <CardHeader className="space-y-3">
            <div className="flex items-center justify-between">
              <Badge variant="secondary" className="rounded-full px-3 py-1">
                Alice Web
              </Badge>
              <ModeToggle />
            </div>
            <div>
              <CardTitle className="text-2xl">Set up this home</CardTitle>
              <CardDescription className="pt-1">
                Create the first local owner account and define the initial rooms for this Alice
                home.
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
            <form className="grid gap-4 md:grid-cols-2" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="siteName">Home Name</Label>
                <Input
                  id="siteName"
                  value={siteName}
                  onChange={(event) => onSiteNameChange(event.target.value)}
                  placeholder="Alice Home"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="timezone">Timezone</Label>
                <Input
                  id="timezone"
                  value={timezone}
                  onChange={(event) => onTimezoneChange(event.target.value)}
                  placeholder="Europe/London"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="ownerName">Owner Name</Label>
                <Input
                  id="ownerName"
                  autoComplete="name"
                  value={ownerDisplayName}
                  onChange={(event) => onOwnerDisplayNameChange(event.target.value)}
                  placeholder="Your name"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="ownerEmail">Owner Email</Label>
                <Input
                  id="ownerEmail"
                  autoComplete="email"
                  value={ownerEmail}
                  onChange={(event) => onOwnerEmailChange(event.target.value)}
                  placeholder="you@home.local"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="setupPassword">Password</Label>
                <Input
                  id="setupPassword"
                  type="password"
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => onPasswordChange(event.target.value)}
                  placeholder="At least 8 characters"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="setupPasswordConfirm">Confirm Password</Label>
                <Input
                  id="setupPasswordConfirm"
                  type="password"
                  autoComplete="new-password"
                  value={passwordConfirm}
                  onChange={(event) => onPasswordConfirmChange(event.target.value)}
                  placeholder="Repeat password"
                />
              </div>

              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="roomNames">Rooms</Label>
                <Input
                  id="roomNames"
                  value={roomNames}
                  onChange={(event) => onRoomNamesChange(event.target.value)}
                  placeholder="Living Room, Kitchen, Dining Room, Downstairs Bathroom, Upstairs Bathroom, Master Bedroom, Kids Room"
                />
                <p className="text-xs text-muted-foreground">
                  Comma-separated room names. Start with the suggested list and adapt it to the
                  actual home.
                </p>
              </div>

              {setupError ? (
                <div className="md:col-span-2">
                  <Alert variant="destructive">
                    <AlertTitle>Setup failed</AlertTitle>
                    <AlertDescription>{setupError}</AlertDescription>
                  </Alert>
                </div>
              ) : null}

              <div className="md:col-span-2">
                <Button className="w-full" disabled={isSubmitting} type="submit">
                  {isSubmitting ? "Finishing setup..." : "Finish setup"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
