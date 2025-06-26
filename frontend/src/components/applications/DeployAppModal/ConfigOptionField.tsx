
import React, { useEffect, useState } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { ConfigOption } from "@/types";
import * as api from "@/services/api";

interface ConfigOptionFieldProps {
  option: ConfigOption;
  value: any;
  updateConfig: (optionId: string, value: any) => void;
  config?: Record<string, any>;
}

const ConfigOptionField: React.FC<ConfigOptionFieldProps> = ({
  option,
  value,
  updateConfig,
  config = {}
}) => {
  const [versions, setVersions] = useState<string[]>([]);

  useEffect(() => {
    const fetchVersions = async () => {
      if (option.id === "version") {
        try {
          const appId = option.applicationId?.toString();
          if (appId) {
            const availableVersions = await api.getApplicationVersions(appId);
            setVersions(availableVersions);
          }
        } catch (error) {
          console.error("Error fetching versions:", error);
        }
      }
    };

    fetchVersions();
  }, [option.id, option.applicationId]);

  // Check if this field should be disabled
  const isDisabled = option.id === "version" && config.use_custom_image;

  switch (option.type) {
    case "text":
      return (
        <div className="space-y-2">
          <Label htmlFor={option.id}>{option.name}</Label>
          {option.id === "dags_repository_ssh_private_key" || option.id === "private_registry_password" ? (
            <Input
              id={option.id}
              type="password"
              value={value || ""}
              onChange={e => updateConfig(option.id, e.target.value)}
              placeholder={option.description}
              disabled={isDisabled}
            />
          ) : (
            <Input
              id={option.id}
              value={value || ""}
              onChange={e => updateConfig(option.id, e.target.value)}
              placeholder={option.description}
              disabled={isDisabled}
            />
          )}
          <p className="text-xs text-muted-foreground">
            {option.required ? "Required" : "Optional"}: {option.description}
            {isDisabled && " (Disabled when using custom image)"}
          </p>
        </div>
      );

    case "number":
      return (
        <div className="space-y-2">
          <Label htmlFor={option.id}>{option.name}</Label>
          <Input
            id={option.id}
            type="number"
            value={value || ""}
            onChange={e => updateConfig(option.id, parseInt(e.target.value))}
            placeholder={option.description}
            disabled={isDisabled}
          />
          <p className="text-xs text-muted-foreground">
            {option.required ? "Required" : "Optional"}: {option.description}
            {isDisabled && " (Disabled when using custom image)"}
          </p>
        </div>
      );

    case "select":
      return (
        <div className="space-y-2">
          <Label htmlFor={option.id}>{option.name}</Label>
          <Select
            value={value || ""}
            onValueChange={(val) => updateConfig(option.id, val)}
            disabled={isDisabled}
          >
            <SelectTrigger id={option.id}>
              <SelectValue placeholder={option.description} />
            </SelectTrigger>
            <SelectContent>
              {option.id === "version" && versions.length > 0
                ? versions.map((version) => (
                    <SelectItem key={version} value={version}>{version}</SelectItem>
                  ))
                : option.options?.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {option.required ? "Required" : "Optional"}: {option.description}
            {isDisabled && " (Disabled when using custom image)"}
          </p>
        </div>
      );

    case "boolean":
      return (
        <div className="flex items-center justify-between mb-4">
          <div>
            <Label htmlFor={option.id}>{option.name}</Label>
            <p className="text-xs text-muted-foreground">{option.description}</p>
          </div>
          <Switch
            id={option.id}
            checked={!!value}
            onCheckedChange={checked => updateConfig(option.id, checked)}
          />
        </div>
      );

    default:
      return null;
  }
};

export default ConfigOptionField;
