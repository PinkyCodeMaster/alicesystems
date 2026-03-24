import { FormEvent } from "react";

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { AutoLightSettings, Entity, formatDate } from "@/lib/alice-client";

export function AutoLightForm({
  autoLight,
  entities,
  saving,
  onSubmit,
  onChange,
}: {
  autoLight: AutoLightSettings;
  entities: Entity[];
  saving: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onChange: (next: AutoLightSettings) => void;
}) {
  const sensorOptions = entities.filter((entity) => entity.kind === "sensor.illuminance");
  const targetOptions = entities.filter(
    (entity) => entity.kind === "switch.relay" && entity.writable === 1,
  );

  return (
    <Card className="rounded-3xl">
      <CardHeader>
        <CardTitle>Auto-light configuration</CardTitle>
        <CardDescription>
          Stored in SQLite and editable without touching environment config.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={onSubmit}>
          <div className="flex items-center justify-between rounded-2xl border p-4">
            <div>
              <Label htmlFor="enabled" className="text-sm font-medium">
                Enabled
              </Label>
              <p className="text-xs text-muted-foreground">
                Toggle the automation on or off.
              </p>
            </div>
            <Switch
              id="enabled"
              checked={autoLight.enabled}
              onCheckedChange={(checked) =>
                onChange({ ...autoLight, enabled: checked })
              }
            />
          </div>

          <div className="space-y-2">
            <Label>Mode</Label>
            <Select
              value={autoLight.mode}
              onValueChange={(value) => {
                if (!value) {
                  return;
                }
                onChange({ ...autoLight, mode: value });
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="lux_low_turn_on">lux_low_turn_on</SelectItem>
                <SelectItem value="raw_high_turn_on">raw_high_turn_on</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Sensor entity</Label>
              <Select
                value={autoLight.sensor_entity_id ?? "none"}
                onValueChange={(value) => {
                  if (!value) {
                    return;
                  }
                  onChange({
                    ...autoLight,
                    sensor_entity_id: value === "none" ? null : value,
                  });
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select sensor entity" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Not set</SelectItem>
                  {sensorOptions.map((entity) => (
                    <SelectItem key={entity.id} value={entity.id}>
                      {entity.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Target entity</Label>
              <Select
                value={autoLight.target_entity_id ?? "none"}
                onValueChange={(value) => {
                  if (!value) {
                    return;
                  }
                  onChange({
                    ...autoLight,
                    target_entity_id: value === "none" ? null : value,
                  });
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select target entity" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Not set</SelectItem>
                  {targetOptions.map((entity) => (
                    <SelectItem key={entity.id} value={entity.id}>
                      {entity.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="on_raw">On raw</Label>
              <Input
                id="on_raw"
                type="number"
                value={autoLight.on_raw}
                onChange={(event) =>
                  onChange({ ...autoLight, on_raw: Number(event.target.value) })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="off_raw">Off raw</Label>
              <Input
                id="off_raw"
                type="number"
                value={autoLight.off_raw}
                onChange={(event) =>
                  onChange({ ...autoLight, off_raw: Number(event.target.value) })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="on_lux">On lux</Label>
              <Input
                id="on_lux"
                type="number"
                value={autoLight.on_lux}
                onChange={(event) =>
                  onChange({ ...autoLight, on_lux: Number(event.target.value) })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="off_lux">Off lux</Label>
              <Input
                id="off_lux"
                type="number"
                value={autoLight.off_lux}
                onChange={(event) =>
                  onChange({ ...autoLight, off_lux: Number(event.target.value) })
                }
              />
            </div>
          </div>

          <Separator />

          <div className="space-y-1 text-xs text-muted-foreground">
            <p>Source: {autoLight.source}</p>
            <p>Updated: {formatDate(autoLight.updated_at)}</p>
          </div>

          <Button className="w-full" disabled={saving} type="submit">
            {saving ? "Saving..." : "Save auto-light"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
