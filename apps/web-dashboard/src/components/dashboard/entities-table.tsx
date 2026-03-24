import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Entity, EntityState, formatState } from "@/lib/alice-client";

export function EntitiesTable({
  entities,
  states,
  busyEntityId,
  onRelayCommand,
}: {
  entities: Entity[];
  states: Record<string, EntityState>;
  busyEntityId?: string | null;
  onRelayCommand?: (entityId: string, on: boolean) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-2xl border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Entity</TableHead>
            <TableHead>Capability</TableHead>
            <TableHead>State</TableHead>
            <TableHead className="w-[180px]">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entities.map((entity) => (
            <TableRow key={entity.id}>
              <TableCell className="align-top">
                <div className="font-medium">{entity.name}</div>
                <div className="text-xs text-muted-foreground">
                  {entity.id} | {entity.device_id}
                </div>
              </TableCell>
              <TableCell>{entity.kind}</TableCell>
              <TableCell className="max-w-[360px] text-sm text-muted-foreground">
                {formatState(states[entity.id]?.value)}
              </TableCell>
              <TableCell>
                {entity.writable === 1 && onRelayCommand ? (
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      disabled={busyEntityId === entity.id}
                      onClick={() => onRelayCommand(entity.id, true)}
                      type="button"
                    >
                      On
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busyEntityId === entity.id}
                      onClick={() => onRelayCommand(entity.id, false)}
                      type="button"
                    >
                      Off
                    </Button>
                  </div>
                ) : (
                  <Badge variant="outline">
                    {entity.writable === 1 ? "Action unavailable" : "Read-only"}
                  </Badge>
                )}
              </TableCell>
            </TableRow>
          ))}

          {entities.length === 0 ? (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground">
                No entities found.
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </div>
  );
}
