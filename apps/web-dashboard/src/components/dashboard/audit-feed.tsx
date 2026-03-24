import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { AuditEvent, formatDate, parseMetadata } from "@/lib/alice-client";

export function AuditFeed({
  events,
  emptyMessage,
}: {
  events: AuditEvent[];
  emptyMessage?: string;
}) {
  if (events.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {emptyMessage ?? "No recent audit events."}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {events.map((event) => (
        <div key={event.id} className="space-y-3 rounded-2xl border p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              <Badge variant={event.severity === "warning" ? "secondary" : "default"}>
                {event.action}
              </Badge>
              <p className="text-xs text-muted-foreground">
                {formatDate(event.created_at)}
              </p>
            </div>
          </div>

          <div className="text-xs text-muted-foreground">
            target: {event.target_id ?? "n/a"} | actor: {event.actor_id ?? "system"}
          </div>

          <Textarea
            readOnly
            value={JSON.stringify(parseMetadata(event.metadata_json), null, 2)}
            className="min-h-[120px] font-mono text-xs"
          />
        </div>
      ))}
    </div>
  );
}
