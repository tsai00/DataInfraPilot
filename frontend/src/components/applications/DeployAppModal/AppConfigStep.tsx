
import React, { useState, useEffect } from 'react';
import { Application, ConfigOption } from "@/types";
import ConfigOptionField from './ConfigOptionField';
import { Separator } from '@/components/ui/separator';
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { useClusterStore } from "@/store";

interface AppConfigStepProps {
  selectedApp: Application;
  appModule: any;
  config: Record<string, any>;
  updateConfig: (optionId: string, value: any) => void;
  clusterId: string;
}

const AppConfigStep: React.FC<AppConfigStepProps> = ({
    selectedApp,
    appModule,
    config,
    updateConfig,
    clusterId
}) => {
  const { clusters } = useClusterStore();
  const [deploymentNameError, setDeploymentNameError] = useState<string>("");

  // Find the current cluster
  const currentCluster = clusters.find(c => c.id === clusterId);

  // Check for duplicate deployment names
  useEffect(() => {
    if (config.deployment_name && currentCluster) {
      const existingDeployment = currentCluster.deployments.find(
        deployment => deployment.name.toLowerCase() === config.deployment_name.toLowerCase()
      );

      if (existingDeployment) {
        setDeploymentNameError("A deployment with this name already exists in this cluster");
      } else {
        setDeploymentNameError("");
      }
    } else {
      setDeploymentNameError("");
    }
  }, [config.deployment_name, currentCluster]);

  // Function to determine if conditional field should be shown
  const shouldShowField = (option: ConfigOption) => {
    if (option.conditional) {
      return config[option.conditional.field] === option.conditional.value;
    }

    // Special case for Airflow Flower enabled field - only show if CeleryExecutor is selected
    if (option.id === 'flower_enabled' && selectedApp.short_name === 'airflow') {
      const isCeleryExecutor = config.executor === 'CeleryExecutor';
      console.log(`Checking field ${option.id}: isCeleryExecutor=${isCeleryExecutor}, executor=${config.executor}`);
      return isCeleryExecutor;
    }

    return true;
  };

  return (
    <div className="space-y-6 py-4">
        <div className="border rounded-lg p-4 bg-secondary/30">
        <div className="flex items-start gap-4">
            <img
            src={selectedApp?.logo}
            alt={selectedApp?.name}
            className="w-16 h-16 object-contain bg-white rounded-lg p-2"
            />
            <div className="flex-1">
            <h3 className="font-medium text-lg">{selectedApp?.name}</h3>
            <p className="text-sm text-muted-foreground">
                {selectedApp?.description}
            </p>
            <div className="mt-2 px-3 py-1 rounded-lg bg-muted/100 border text-xs flex flex-row items-center gap-2 text-muted-foreground">
                <div className="flex flex-row items-center gap-2">
                <span className="font-medium">Minimal recommended resources:</span>&nbsp;{appModule?.appRecommendedResources.nodes} nodes • {appModule?.appRecommendedResources.ram} RAM • {appModule?.appRecommendedResources.cpu}
                </div>
            </div>
            </div>
        </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="deployment_name">Deployment Name</Label>
          <Input
              id="deployment_name"
              value={config.deployment_name || ""}
              onChange={e => updateConfig("deployment_name", e.target.value)}
              placeholder={`e.g. ${selectedApp.name} (Staging)`}
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
        <div className="space-y-4">
        <h3 className="font-medium">Configuration Options</h3>
        <div className="space-y-6 border rounded-lg p-4 bg-secondary/10">
            {(appModule?.configOptions || selectedApp?.configOptions || [])
            .filter((opt: ConfigOption) => shouldShowField(opt))
            .map((opt: ConfigOption) => {
                console.log(`Rendering field: ${opt.id}, shouldShow: ${shouldShowField(opt)}`);
                return (
                    <ConfigOptionField
                        key={opt.id}
                        option={opt}
                        value={config[opt.id]}
                        updateConfig={updateConfig}
                        config={config}
                    />
                );
            })
            }
        </div>
        </div>
    </div>
  );
};

export default AppConfigStep;
