import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Device, formatDate, getStatusVariant } from "@/lib/alice-client";

export function DevicesTable({ devices }: { devices: Device[] }) {
  return (
    <div className="overflow-x-auto rounded-2xl border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Last seen</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {devices.map((device) => (
            <TableRow key={device.id}>
              <TableCell className="min-w-[280px] align-top">
                <Link
                  className="font-medium underline-offset-4 hover:underline"
                  href={`/devices/${device.id}`}
                >
                  {device.name}
                </Link>
                <div className="text-xs text-muted-foreground">
                  {device.id} | {device.model} | fw {device.fw_version ?? "unknown"}
                </div>
              </TableCell>
              <TableCell>{device.device_type}</TableCell>
              <TableCell>
                <Badge variant={getStatusVariant(device.status)}>{device.status}</Badge>
              </TableCell>
              <TableCell>{formatDate(device.last_seen_at)}</TableCell>
            </TableRow>
          ))}
          {devices.length === 0 ? (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground">
                No devices found.
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </div>
  );
}
