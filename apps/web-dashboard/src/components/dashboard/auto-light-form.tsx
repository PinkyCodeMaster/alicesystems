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
  const motionOptions = entities.filter((entity) => entity.kind === "sensor.motion");
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
            <div className="flex items-center justify-between rounded-2xl border p-4 sm:col-span-2">
              <div>
                <Label htmlFor="block_on_during_daytime" className="text-sm font-medium">
                  Block turn-on during daytime
                </Label>
                <p className="text-xs text-muted-foreground">
                  Prevent auto-light from turning on during the configured daytime window.
                </p>
              </div>
              <Switch
                id="block_on_during_daytime"
                checked={autoLight.block_on_during_daytime}
                onCheckedChange={(checked) =>
                  onChange({ ...autoLight, block_on_during_daytime: checked })
                }
              />
            </div>

            <div className="flex items-center justify-between rounded-2xl border p-4 sm:col-span-2">
              <div>
                <Label
                  htmlFor="allow_daytime_turn_on_when_very_dark"
                  className="text-sm font-medium"
                >
                  Allow daytime turn-on when very dark
                </Label>
                <p className="text-xs text-muted-foreground">
                  Lets the light turn on in daytime only when the room is genuinely dark.
                </p>
              </div>
              <Switch
                id="allow_daytime_turn_on_when_very_dark"
                checked={autoLight.allow_daytime_turn_on_when_very_dark}
                onCheckedChange={(checked) =>
                  onChange({
                    ...autoLight,
                    allow_daytime_turn_on_when_very_dark: checked,
                  })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="daytime_on_lux">Daytime override lux</Label>
              <Input
                id="daytime_on_lux"
                type="number"
                value={autoLight.daytime_on_lux}
                onChange={(event) =>
                  onChange({
                    ...autoLight,
                    daytime_on_lux: Number(event.target.value),
                  })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="daytime_on_raw">Daytime override raw</Label>
              <Input
                id="daytime_on_raw"
                type="number"
                value={autoLight.daytime_on_raw}
                onChange={(event) =>
                  onChange({
                    ...autoLight,
                    daytime_on_raw: Number(event.target.value),
                  })
                }
              />
            </div>

            <div className="flex items-center justify-between rounded-2xl border p-4 sm:col-span-2">
              <div>
                <Label htmlFor="require_motion_for_turn_on" className="text-sm font-medium">
                  Require recent motion for turn-on
                </Label>
                <p className="text-xs text-muted-foreground">
                  Prevents daytime or nighttime auto turn-on unless recent occupancy was seen.
                </p>
              </div>
              <Switch
                id="require_motion_for_turn_on"
                checked={autoLight.require_motion_for_turn_on}
                onCheckedChange={(checked) =>
                  onChange({ ...autoLight, require_motion_for_turn_on: checked })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="daytime_start_hour">Daytime start hour</Label>
              <Input
                id="daytime_start_hour"
                type="number"
                min={0}
                max={23}
                value={autoLight.daytime_start_hour}
                onChange={(event) =>
                  onChange({
                    ...autoLight,
                    daytime_start_hour: Number(event.target.value),
                  })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="daytime_end_hour">Daytime end hour</Label>
              <Input
                id="daytime_end_hour"
                type="number"
                min={0}
                max={23}
                value={autoLight.daytime_end_hour}
                onChange={(event) =>
                  onChange({
                    ...autoLight,
                    daytime_end_hour: Number(event.target.value),
                  })
                }
              />
            </div>

            <div className="space-y-2">
              <Label>Motion entity</Label>
              <Select
                value={autoLight.motion_entity_id ?? "none"}
                onValueChange={(value) => {
                  if (!value) {
                    return;
                  }
                  onChange({
                    ...autoLight,
                    motion_entity_id: value === "none" ? null : value,
                  });
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select motion entity" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Not set</SelectItem>
                  {motionOptions.map((entity) => (
                    <SelectItem key={entity.id} value={entity.id}>
                      {entity.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="motion_hold_seconds">Motion hold seconds</Label>
              <Input
                id="motion_hold_seconds"
                type="number"
                min={0}
                value={autoLight.motion_hold_seconds}
                onChange={(event) =>
                  onChange({
                    ...autoLight,
                    motion_hold_seconds: Number(event.target.value),
                  })
                }
              />
            </div>

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
