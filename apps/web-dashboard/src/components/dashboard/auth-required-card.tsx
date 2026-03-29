import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function AuthRequiredCard({
  title = "Login required",
  description = "Return to Alice Web and sign in before opening this page.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-4">
        <Card className="w-full rounded-3xl">
          <CardHeader>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </CardHeader>
          <CardContent>
            <Link className="inline-flex" href="/">
              <Button type="button">Back to Alice Web</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
