import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { StepProgress } from "@/components/StepProgress";
import { useClusterStore } from "@/store";
import { Application, ConfigOption, AccessEndpoint, AccessEndpointConfig, AccessEndpointType } from "@/types";
import { useToast } from "@/hooks/use-toast";
import AccessConfigStep from "./DeployAppModal/AccessConfigStep";
import AirflowDeployConfig from "./appConfigs/airflow";
import GrafanaDeployConfig from "./appConfigs/grafana";
import SparkDeployConfig from "./appConfigs/spark";
import { getApplicationAccessEndpoints, checkEndpointExistence } from "@/services/api";
import AppSelectionStep from "./DeployAppModal/AppSelectionStep";
import AppConfigStep from "./DeployAppModal/AppConfigStep";
import NodePoolConfigStep from "./DeployAppModal/NodePoolConfigStep";
import StorageConfigStep from "./DeployAppModal/StorageConfigStep";

const appDeployModules: Record<string, any> = {
  airflow: AirflowDeployConfig,
  grafana: GrafanaDeployConfig,
  spark: SparkDeployConfig
};

interface DeployAppModalProps {
  open: boolean;
  onClose: () => void;
  clusterId: string;
}

const steps = [
  { id: "selection", label: "Select Application" },
  { id: "configuration", label: "Configure" },
  { id: "volumes", label: "Storage" },
  { id: "nodepool", label: "Node Pool" },
  { id: "access", label: "Access Configuration" },
];

const DeployAppModal: React.FC<DeployAppModalProps> = ({
  open,
  onClose,
  clusterId,
}) => {
  const { applications, createDeployment, clusters } = useClusterStore();
  const { toast } = useToast();

  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [config, setConfig] = useState<Record<string, any>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isValidatingEndpoints, setIsValidatingEndpoints] = useState(false);
  const [step, setStep] = useState<"selection" | "configuration" | "volumes" | "nodepool" | "access">("selection");
  const [selectedNodePool, setSelectedNodePool] = useState<string>("noselection");
  const [volumeSelections, setVolumeSelections] = useState<Array<{
    size: number;
    name: string;
    volume_type: string;
  }>>([]);

  const [accessEndpoints, setAccessEndpoints] = useState<AccessEndpoint[]>([]);
  const [endpointConfigs, setEndpointConfigs] = useState<AccessEndpointConfig[]>([]);
  const [isLoadingEndpoints, setIsLoadingEndpoints] = useState(false);

  const clusterName =
    clusters.find((c) => c.id === clusterId)?.name || "this cluster";
  
  const cluster = clusters.find((c) => c.id === clusterId);
  const workerNodePools = cluster?.nodePools || [];

  const appModule = selectedApp ? appDeployModules[selectedApp.short_name] : undefined;

  useEffect(() => {
    if (open) {
      setSelectedApp(null);
      setConfig({});
      setIsSubmitting(false);
      setStep("selection");
      setVolumeSelections([]);
      setAccessEndpoints([]);
      setEndpointConfigs([]);
    }
  }, [open]);

  // Fetch access endpoints when selecting an app or before entering the access configuration step
  useEffect(() => {
    const fetchAccessEndpoints = async () => {
      if (!selectedApp) return;
      
      try {
        setIsLoadingEndpoints(true);
        const endpoints = await getApplicationAccessEndpoints(selectedApp.id.toString());
        console.log("Fetched access endpoints:", endpoints);
        setAccessEndpoints(endpoints);
        
        // Initialize endpoint configurations with defaults
        const initialConfigs: AccessEndpointConfig[] = endpoints.map(endpoint => ({
          name: endpoint.name,
          access_type: endpoint.default_access,
          value: endpoint.default_value
        }));
        setEndpointConfigs(initialConfigs);
      } catch (error) {
        console.error("Failed to fetch access endpoints:", error);

        toast({
          title: "Failed to fetch application Access Endpoints",
          description: `Error ${error}`,
          variant: "destructive",
        });
      } finally {
        setIsLoadingEndpoints(false);
      }
    };

    if (selectedApp && (step === "access" || step === "nodepool")) {
      fetchAccessEndpoints();
    }
  }, [selectedApp, step, cluster.domainName, toast]);

  useEffect(() => {
    if (selectedApp) {
      console.log("Select app: " + JSON.stringify(selectedApp))
      const module = appDeployModules[selectedApp.short_name];
      const filteredOpts = module?.configOptions || selectedApp.configOptions;
      const initialConfig = {
        ...filteredOpts.reduce((acc, option) => {
          if (option.default !== undefined) {
            acc[option.id] = option.default;
          }
          return acc;
        }, {} as Record<string, any>)
      };

      setConfig(initialConfig);

      if (selectedApp.volumeRequirements) {
        setVolumeSelections(selectedApp.volumeRequirements.map(vol => ({
          volume_type: "existing",
          size: vol.defaultSize,
          name: vol.name
        })));
      }
    }
  }, [selectedApp]);

  const handleAppSelect = (app: Application) => {
    setSelectedApp(app);
    setStep("configuration");
  };

  const updateConfig = (optionId: string, value: any) => {
    setConfig((prev) => {
      return { ...prev, [optionId]: value };
    });
  };

  const updateVolumeSelection = (volumeType?: string, size?: number, name?: string) => {
    setVolumeSelections(prev => prev.map(vol => 
      vol.name === name 
        ? { 
            ...vol, 
            size: size || vol.size,
            name: name || vol.name,
            volumeType: volumeType || vol.volume_type
          }
        : vol
    ));
  };

  const isAirflow =
    selectedApp && (selectedApp.short_name === "airflow" || selectedApp.id === 1);

  const validateEndpoints = async (formattedEndpoints: AccessEndpointConfig[]): Promise<boolean> => {
    try {
      setIsValidatingEndpoints(true);
      
      // Check each endpoint individually
      for (const endpoint of formattedEndpoints) {
        const exists = await checkEndpointExistence(clusterId, endpoint);
        
        if (exists) {
          toast({
            title: "Endpoint conflict detected",
            description: `The endpoint path "${endpoint.value}" already exists. Please choose a different path.`,
            variant: "destructive",
          });
          return false;
        }
      }
      
      return true;
    } catch (error) {
      console.error("Failed to validate endpoints:", error);
      toast({
        title: "Validation failed",
        description: "Failed to validate endpoint availability. Please try again.",
        variant: "destructive",
      });
      return false;
    } finally {
      setIsValidatingEndpoints(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedApp) {
      toast({
        title: "No application selected",
        description: "Please select an application to deploy.",
        variant: "destructive",
      });
      return;
    }

    if (step === "configuration") {
      const result = appDeployModules[selectedApp.short_name].validateConfig(config);

      if (result !== true) {
        toast({
          title: "Missing required fields",
          description: `Please fill in the following fields: ${result.join(", ")}`,
          variant: "destructive",
        });
        return;
      }

      setStep("volumes");
      return;
    }

    if (step === "volumes") {
      setStep("nodepool");
      return;
    }

    if (step === "nodepool") {
      setStep("access");
      return;
    }

    if (step === "access") {
      if (endpointConfigs.length === 0) {
        toast({
          title: "Missing access configuration",
          description: "Please configure at least one endpoint access.",
          variant: "destructive",
        });
        return;
      }

      // Check that all required endpoints are configured
      const requiredEndpoints = accessEndpoints.filter(endpoint => endpoint.required);
      const missingRequiredEndpoints = requiredEndpoints.filter(
        endpoint => !endpointConfigs.some(config => config.name === endpoint.name)
      );

      if (missingRequiredEndpoints.length > 0) {
        toast({
          title: "Missing required endpoints",
          description: `Please configure the following required endpoints: ${missingRequiredEndpoints.map(e => e.description).join(", ")}`,
          variant: "destructive",
        });
        return;
      }

      // Validate that all endpoint configs have values
      const invalidEndpoints = endpointConfigs.filter(config => !config.value);
      if (invalidEndpoints.length > 0) {
        toast({
          title: "Invalid endpoint configurations",
          description: "All enabled endpoints must have a path or subdomain value.",
          variant: "destructive",
        });
        return;
      }

      // Format endpoint configs for the backend
      const formattedEndpoints = endpointConfigs.map(config => {
        let formattedValue = config.value;

        // For paths, ensure they start with a '/'
        if ((config.access_type === AccessEndpointType.DOMAIN_PATH || AccessEndpointType.CLUSTER_IP_PATH) && !formattedValue.startsWith('/')) {
          formattedValue = `/${formattedValue}`;
        }
        
        // For subdomains, include the full domain name if it's not already included
        if (config.access_type === AccessEndpointType.SUBDOMAIN && cluster?.domainName) {
          if (!formattedValue.includes('.')) {
            formattedValue = `${formattedValue}.${cluster.domainName}`;
          }
        } else if (config.access_type === AccessEndpointType.DOMAIN_PATH && cluster?.domainName) {
          formattedValue = `${cluster.domainName}${formattedValue}`;
        }
        
        
        return {
          ...config,
          value: formattedValue
        };
      });

      // Validate endpoints before submitting
      const isValid = await validateEndpoints(formattedEndpoints);
      if (!isValid) {
        return;
      }

      setIsSubmitting(true);
      
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

      createDeployment(
        clusterId, 
        selectedApp, 
        finalConfig, 
        selectedNodePool,
        volumeSelections,
        formattedEndpoints
      );

      toast({
        title: "Application deployment started",
        description: `${selectedApp.name} is being deployed to ${clusterName}. This may take a few minutes.`,
      });

      onClose();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px] overflow-y-auto max-h-[85vh]">
        <DialogHeader>
          <DialogTitle>Deploy Application to Cluster</DialogTitle>
          <DialogDescription>
            {step === "selection"
              ? "Select a data engineering application to deploy."
              : step === "configuration"
              ? `Configure ${selectedApp?.name} before deployment to ${clusterName}.`
              : step === "volumes"
              ? "Configure storage volumes for the application."
              : step === "nodepool"
              ? "Select a worker node pool for deployment."
              : "Configure how the application will be accessed."}
          </DialogDescription>
        </DialogHeader>

        <div className="relative">
          <StepProgress 
            steps={steps} 
            currentStep={steps.findIndex((s) => s.id === step) + 1} 
          />
          
          {step === "selection" ? (
            <AppSelectionStep
              applications={applications}
              appDeployModules={appDeployModules}
              handleAppSelect={handleAppSelect}
            />
          ) : step === "configuration" ? (
            <AppConfigStep
              selectedApp={selectedApp}
              appModule={appModule}
              config={config}
              updateConfig={updateConfig}
            />
          ) : step === "volumes" ? (
            <StorageConfigStep
              selectedApp={selectedApp}
              providerId={cluster.provider.id}
              updateVolumeSelection={updateVolumeSelection}
            />
          ) : step === "nodepool" ? (
            <NodePoolConfigStep
              selectedNodePool={selectedNodePool}
              workerNodePools={workerNodePools}
              setSelectedNodePool={setSelectedNodePool}
            />
          ) : (
            <AccessConfigStep
              cluster={cluster}
              accessEndpoints={accessEndpoints}
              endpointConfigs={endpointConfigs}
              setEndpointConfigs={setEndpointConfigs}
              applicationConfig={config}
            />
          )}

          <DialogFooter>
            {step !== "selection" && (
              <Button
                variant="outline"
                onClick={() => setStep(
                  step === "access" ? "nodepool" :
                  step === "nodepool" ? "volumes" :
                  step === "volumes" ? "configuration" : "selection"
                )}
                disabled={isSubmitting || isLoadingEndpoints || isValidatingEndpoints}
              >
                Back
              </Button>
            )}
            {step === "selection" ? (
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
            ) : (
              <Button onClick={handleSubmit} disabled={!selectedApp || isSubmitting || isLoadingEndpoints || isValidatingEndpoints}>
                {isLoadingEndpoints ? "Loading..." : 
                 isValidatingEndpoints ? "Validating access endpoints..." :
                 step === "access" ? "Deploy Application" : "Next"}
              </Button>
            )}
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default DeployAppModal;
