import type { ComponentType } from "react";

import { Card, CardContent } from "@/components/ui/card";

export function StatCard({
  title,
  value,
  icon: Icon,
  hint,
}: {
  title: string;
  value: number | string;
  icon: ComponentType<{ className?: string }>;
  hint?: string;
}) {
  return (
    <Card className="rounded-2xl shadow-sm">
      <CardContent className="flex items-center justify-between p-6">
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-3xl font-semibold tracking-tight">{value}</p>
          {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
        </div>
        <div className="rounded-2xl border bg-muted p-3">
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}
