
import React, { useMemo, useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Application, ConfigOption } from "@/types";
import { Button } from "@/components/ui/button";
import { useClusterStore } from "@/store";
import { useToast } from "@/hooks/use-toast";
import { Card } from "@/components/ui/card";
import ConfigOptionField from "./DeployAppModal/ConfigOptionField";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

// Import per-app deploy configs (mirroring DeployAppModal)
import AirflowDeployConfig from "./appConfigs/airflow";
import GrafanaDeployConfig from "./appConfigs/grafana";
import SparkDeployConfig from "./appConfigs/spark";

const appDeployModules: Record<string, any> = {
  airflow: AirflowDeployConfig,
  grafana: GrafanaDeployConfig,
  spark: SparkDeployConfig
};

interface UpdateConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  application: Application;
  currentConfig: Record<string, any>;
  clusterId: string;
  appId: string;
}

const UpdateConfigDialog: React.FC<UpdateConfigDialogProps> = ({
  open,
  onOpenChange,
  application,
  currentConfig,
  clusterId,
  appId,
}) => {
  const { updateDeployment: updateApplication, clusters } = useClusterStore();
  const { toast } = useToast();

  // Find the app's module-based config
  const appModule = useMemo(
    () => appDeployModules[application.short_name],
    [application.short_name]
  );

  // Find the current cluster and deployment
  const currentCluster = clusters.find(c => c.id === clusterId);
  const currentDeployment = currentCluster?.deployments.find(d => d.id === appId);

  // Prepopulate config form values from currentConfig (deployed app)
  const [config, setConfig] = useState<Record<string, any>>(() => {
    // If configOptions have default values, fill them in on top of currentConfig
    const opts: ConfigOption[] =
      appModule?.configOptions || application.configOptions || [];
    let initial: Record<string, any> = {};

    // Add deployment name
    initial.deployment_name = currentConfig?.name || "";

    opts.forEach((option) => {
      if (currentConfig && currentConfig[option.id] !== undefined) {
        initial[option.id] = currentConfig[option.id];
      } else if (option.default !== undefined) {
        initial[option.id] = option.default;
      }
    });

    // Airflow-specific legacy fields
    if (application.short_name === "airflow" || application.id === 1) {
      initial.airflowDagRepoUrl = currentConfig?.airflowDagRepoUrl || currentConfig?.dags_repository || "";
      initial.airflowDagRepoBranch = currentConfig?.airflowDagRepoBranch || currentConfig?.dagsRepositoryBranch || "main";
      initial.airflowDagFolder = currentConfig?.airflowDagFolder || currentConfig?.dagFolder || "dags";
      // Also handle ssh key
      initial.airflowSshKey = currentConfig?.airflowSshKey || currentConfig?.dagsRepositorySshPrivateKey || "";
      initial.airflowRepoPrivate = !!currentConfig?.airflowSshKey || !!currentConfig?.dagsRepositorySshPrivateKey;
    }
    return { ...initial };
  });

  const [deploymentNameError, setDeploymentNameError] = useState<string>("");

  const clusterName =
    clusters.find((c) => c.id === clusterId)?.name || "this cluster";

  // Check for duplicate deployment names (excluding current deployment)
  useEffect(() => {
    if (config.deployment_name && currentCluster && currentDeployment) {
      const existingDeployment = currentCluster.deployments.find(
        deployment =>
          deployment.name.toLowerCase() === config.deployment_name.toLowerCase() &&
          deployment.id !== currentDeployment.id // Exclude current deployment
      );

      if (existingDeployment) {
        setDeploymentNameError("A deployment with this name already exists in this cluster");
      } else {
        setDeploymentNameError("");
      }
    } else {
      setDeploymentNameError("");
    }
  }, [config.deployment_name, currentCluster, currentDeployment]);

  const updateConfig = (optionId: string, value: any) => {
    setConfig((prev) => {
      return { ...prev, [optionId]: value };
    });
  };

  const isAirflow =
    application && (application.short_name === "airflow" || application.id === 1);

  // Function to determine if conditional field should be shown
  const shouldShowField = (option: ConfigOption) => {
    if (option.conditional) {
      return config[option.conditional.field] === option.conditional.value;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Check for deployment name error
    if (deploymentNameError) {
      toast({
        title: "Invalid deployment name",
        description: deploymentNameError,
        variant: "destructive",
      });
      return;
    }

    const result = appModule.validateConfig(config);

    if (result !== true) {
      toast({
        title: "Missing required fields",
        description: `Please fill in the following fields: ${result.join(", ")}`,
        variant: "destructive",
      });
      return;
    }

    // Prepare final config object as in DeployAppModal
    let finalConfig = { ...config };

    if (isAirflow) {
      finalConfig = {
        ...finalConfig,
        dags_repository: config.airflowDagRepoUrl,
        dagsRepositoryBranch: config.airflowDagRepoBranch,
        dagFolder: config.airflowDagFolder,
        dagsRepositorySshPrivateKey: config.airflowRepoPrivate ? config.airflowSshKey : "",
      };
    }

    await updateApplication(clusterId, appId, finalConfig);

    toast({
      title: "Configuration Updated",
      description: `${application.name} config updated for ${clusterName}.`,
    });

    onOpenChange(false);
  };

  // Find configOptions to render fields for
  const configOptions: ConfigOption[] =
    appModule?.configOptions || application.configOptions || [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] overflow-y-auto max-h-[85vh]">
        <DialogHeader>
          <DialogTitle>Update Configuration</DialogTitle>
          <DialogDescription>
            Update the configuration for {application.name}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-6">
            <Card className="p-4">
              <div className="space-y-2">
                <Label htmlFor="deployment_name">Deployment Name</Label>
                <Input
                  id="deployment_name"
                  value={config.deployment_name || ""}
                  onChange={e => updateConfig("deployment_name", e.target.value)}
                  placeholder="e.g. Airflow (Staging)"
                  className={deploymentNameError ? "border-red-500" : ""}
                />
                {deploymentNameError ? (
                  <p className="text-xs text-red-500">{deploymentNameError}</p>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    Required: Name of deployment
                  </p>
                )}
              </div>
            </Card>
            {configOptions
              .filter(option => shouldShowField(option))
              .map((option) => (
                <Card key={option.id} className="p-4">
                  <ConfigOptionField
                    option={option}
                    value={config[option.id]}
                    updateConfig={updateConfig}
                  />
                </Card>
            ))}
          </div>
          <div className="flex justify-end space-x-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={Boolean(deploymentNameError)}>Save changes</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default UpdateConfigDialog;
