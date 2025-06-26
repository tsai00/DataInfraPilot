import React, { useState, useEffect, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useClusterStore } from "@/store";
import { Provider, Region, NodeType, NodePool } from "@/types";
import { Plus, Trash, Cloud, Server, DollarSign, MapPin, AlertTriangle, Info, Check, Coins, Calendar, Globe, Link2, ToggleRight } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StepProgress } from "@/components/StepProgress";
import { Switch } from "@/components/ui/switch";
import { calculateClusterEstimatedCost, calculateClusterCostRange, getCostForPeriod } from "@/utils/costCalculations";

interface CreateClusterModalProps {
  open: boolean;
  onClose: () => void;
}

const k3sVersions = [
  { value: "v1.32.3+k3s1", label: "v1.32.3+k3s1 (Kubernetes v1.32.3)" },
  { value: "v1.31.7+k3s1", label: "v1.31.7+k3s1 (Kubernetes v1.31.7)" },
  { value: "v1.30.11+k3s1", label: "v1.30.11+k3s1 (Kubernetes v1.30.11)" },
];

const MAX_NODES_WARNING = 10;

const steps = [
  { id: "basics", label: "Basic Information" },
  { id: "nodes", label: "Node Configuration" },
  { id: "domain", label: "Cluster Access" },
  { id: "components", label: "Additional Components" },
  { id: "review", label: "Review & Create" },
];

const CreateClusterModal: React.FC<CreateClusterModalProps> = ({
  open,
  onClose,
}) => {
  const { providers, createCluster, clusters } = useClusterStore();
  const { toast: uiToast } = useToast();

  const [currentStep, setCurrentStep] = useState(1);
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState("");
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [version, setVersion] = useState(k3sVersions[0].value);

  const [sshPrivateKeyPath, setSshPrivateKeyPath] = useState("~/.ssh/id_rsa");
  const [sshPublicKeyPath, setSshPublicKeyPath] = useState("~/.ssh/id_rsa.pub");
  const [providerApiToken, setProviderApiToken] = useState("");

  const [controlPlane, setControlPlane] = useState<NodePool | null>(null);

  const [nodePools, setNodePools] = useState<NodePool[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [totalNodeCount, setTotalNodeCount] = useState(0);
  const [showNodeCountWarning, setShowNodeCountWarning] = useState(false);
  const [useDomainName, setUseDomainName] = useState(false);
  const [domainName, setDomainName] = useState("");

  // Track if this is the initial setup to know when to add default pool
  const [isInitialSetup, setIsInitialSetup] = useState(true);

  // Updated state for additional components
  const [additionalComponents, setAdditionalComponents] = useState({
    traefik_dashboard: {
      enabled: true,
      username: "admin",
      password: ""
    }
  });

  // Reference for dialog content to scroll to top
  const dialogContentRef = useRef<HTMLDivElement>(null);

  // Check if cluster name already exists
  const checkClusterNameExists = (clusterName: string) => {
    if (!clusterName.trim()) {
      setNameError("");
      return false;
    }

    const exists = clusters.some(cluster =>
      cluster.name.toLowerCase() === clusterName.toLowerCase()
    );

    if (exists) {
      setNameError("A cluster with this name already exists");
      return true;
    } else {
      setNameError("");
      return false;
    }
  };

  // Handle name change with validation
  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newName = e.target.value;
    setName(newName);
    checkClusterNameExists(newName);
  };

  useEffect(() => {
    if (open) {
      setCurrentStep(1);
      setName("");
      setNameError("");
      setSelectedProvider(null);
      setVersion(k3sVersions[0].value);
      setSshPrivateKeyPath("~/.ssh/id_rsa");
      setSshPublicKeyPath("~/.ssh/id_rsa.pub");
      setControlPlane(null);
      setNodePools([]);
      setIsSubmitting(false);
      setTotalNodeCount(0);
      setShowNodeCountWarning(false);
      setUseDomainName(false);
      setDomainName("");
      setIsInitialSetup(true); // Reset initial setup flag when modal opens
      setAdditionalComponents({
        traefik_dashboard: {
          enabled: true,
          username: "admin",
          password: ""
        }
      });
    }
  }, [open]);

  // Effect to scroll to top when step changes
  useEffect(() => {
    if (dialogContentRef.current) {
      dialogContentRef.current.scrollTop = 0;
    }
  }, [currentStep]);

  // Handle SSH key path change
  const handlePrivateKeyPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newPrivateKeyPath = e.target.value;
    setSshPrivateKeyPath(newPrivateKeyPath);

    // Automatically update the public key path to match the private key path with .pub suffix
    if (!newPrivateKeyPath.endsWith('.pub')) {
      setSshPublicKeyPath(`${newPrivateKeyPath}.pub`);
    }
  };

  useEffect(() => {
    if (selectedProvider) {
      const availableNodeTypes = selectedProvider.nodeTypes;
      if (availableNodeTypes.length > 0 && selectedProvider.regions.length > 0) {
        setControlPlane({
          id: "control-plane",
          name: "control-plane",
          nodeType: availableNodeTypes[0],
          count: 1,
          region: selectedProvider.regions[0]
        });

        // Only add default node pool during initial setup
        if (nodePools.length === 0 && isInitialSetup) {
          addDefaultNodePool(availableNodeTypes[0], selectedProvider.regions[0]);
          setIsInitialSetup(false); // Mark that initial setup is complete
        }
      }
    }
  }, [selectedProvider, isInitialSetup, nodePools.length]);

  useEffect(() => {
    let total = 0;

    if (controlPlane) {
      total += controlPlane.count;
    }

    nodePools.forEach(pool => {
      total += pool.count;
    });

    setTotalNodeCount(total);
    setShowNodeCountWarning(total > MAX_NODES_WARNING);
  }, [controlPlane, nodePools]);

  const addDefaultNodePool = (nodeType: NodeType, region: Region) => {
    const defaultPool: NodePool = {
      id: `pool-default`,
      name: "default-pool",
      nodeType: nodeType,
      count: 1,
      region: region,
      autoscaling: {
        enabled: false,
        minNodes: 0,
        maxNodes: 1
      }
    };

    setNodePools([defaultPool]);
  };

  const handleProviderSelect = (provider: Provider) => {
    setSelectedProvider(provider);
    // Don't reset nodePools here - let the useEffect handle it
    setControlPlane(null);
  };

  const handleAddNodePool = () => {
    if (!selectedProvider) return;

    const availableNodeTypes = selectedProvider.nodeTypes;
    if (availableNodeTypes.length === 0 || selectedProvider.regions.length === 0) return;

    const newNodePool: NodePool = {
      id: `pool-${Date.now()}`,
      name: `node-pool-${nodePools.length}`,
      nodeType: availableNodeTypes[0],
      count: 1,
      region: selectedProvider.regions[0],
      autoscaling: {
        enabled: false,
        minNodes: 0,
        maxNodes: 1
      }
    };

    setNodePools([...nodePools, newNodePool]);
  };

  const handleRemoveNodePool = (poolId: string) => {
    setNodePools(nodePools.filter((pool) => pool.id !== poolId));
  };

  const handleNodeTypeSelect = (poolId: string, nodeTypeId: string) => {
    if (!selectedProvider) return;

    const nodeType = selectedProvider.nodeTypes.find((nt) => nt.id === nodeTypeId);

    if (nodeType) {
      setNodePools(
        nodePools.map((pool) =>
          pool.id === poolId ? { ...pool, nodeType } : pool
        )
      );
    }
  };

  const handleControlPlaneNodeTypeSelect = (nodeTypeId: string) => {
    if (!selectedProvider || !controlPlane) return;

    const nodeType = selectedProvider.nodeTypes.find((nt) => nt.id === nodeTypeId);

    if (nodeType) {
      setControlPlane({
        ...controlPlane,
        nodeType
      });
    }
  };

  const handleNodeCountChange = (poolId: string, count: number) => {
    if (count < 1) count = 1;
    if (count > 20) count = 20;

    setNodePools(
      nodePools.map((pool) =>
        pool.id === poolId ? { ...pool, count } : pool
      )
    );
  };

  const handleNodePoolNameChange = (poolId: string, name: string) => {
    setNodePools(
      nodePools.map((pool) =>
        pool.id === poolId ? { ...pool, name } : pool
      )
    );
  };

  const handleNodePoolRegionSelect = (poolId: string, regionId: string) => {
    if (!selectedProvider) return;

    const region = selectedProvider.regions.find((r) => r.id === regionId);
    if (region) {
      setNodePools(
        nodePools.map((pool) =>
          pool.id === poolId ? { ...pool, region } : pool
        )
      );
    }
  };

  const handleControlPlaneRegionSelect = (regionId: string) => {
    if (!selectedProvider || !controlPlane) return;

    const region = selectedProvider.regions.find((r) => r.id === regionId);
    if (region) {
      setControlPlane({
        ...controlPlane,
        region
      });
    }
  };

  const handleAutoscalingToggle = (poolId: string, enabled: boolean) => {
    setNodePools(
      nodePools.map((pool) => {
        if (pool.id === poolId) {
          return {
            ...pool,
            autoscaling: {
              enabled,
              minNodes: enabled ? 1 : 0,
              maxNodes: enabled ? Math.max(pool.count, 2) : 1
            }
          };
        }
        return pool;
      })
    );
  };

  const handleMinNodesChange = (poolId: string, minNodes: number) => {
    if (minNodes < 0) minNodes = 0;
    if (minNodes > 10) minNodes = 10;

    setNodePools(
      nodePools.map((pool) => {
        if (pool.id === poolId && pool.autoscaling) {
          // Ensure minNodes doesn't exceed maxNodes
          const adjustedMinNodes = Math.min(minNodes, pool.autoscaling.maxNodes);

          return {
            ...pool,
            autoscaling: {
              ...pool.autoscaling,
              minNodes: adjustedMinNodes
            }
          };
        }
        return pool;
      })
    );
  };

  const handleMaxNodesChange = (poolId: string, maxNodes: number) => {
    if (maxNodes < 1) maxNodes = 1;
    if (maxNodes > 10) maxNodes = 10;

    setNodePools(
      nodePools.map((pool) => {
        if (pool.id === poolId && pool.autoscaling) {
          // Ensure maxNodes isn't less than minNodes
          const adjustedMaxNodes = Math.max(maxNodes, pool.autoscaling.minNodes);

          return {
            ...pool,
            autoscaling: {
              ...pool.autoscaling,
              maxNodes: adjustedMaxNodes
            }
          };
        }
        return pool;
      })
    );
  };

  // Handle changes to the additional components
  const handleTraefikToggle = (enabled: boolean) => {
    setAdditionalComponents(prev => ({
      ...prev,
      traefik_dashboard: {
        ...prev.traefik_dashboard,
        enabled
      }
    }));
  };

  const handleTraefikUsernameChange = (username: string) => {
    setAdditionalComponents(prev => ({
      ...prev,
      traefik_dashboard: {
        ...prev.traefik_dashboard,
        username
      }
    }));
  };

  const handleTraefikPasswordChange = (password: string) => {
    setAdditionalComponents(prev => ({
      ...prev,
      traefik_dashboard: {
        ...prev.traefik_dashboard,
        password
      }
    }));
  };

  const nextStep = () => {
    if (currentStep === 1) {
      if (!name.trim() || !selectedProvider || nameError) {
        uiToast({
          title: "Missing information",
          description: nameError || "Please fill in all required fields to continue.",
          variant: "destructive",
        });
        return;
      }

      if (selectedProvider.id === "hetzner" && (!sshPrivateKeyPath.trim() || !sshPublicKeyPath.trim() || !providerApiToken.trim())) {
        uiToast({
          title: "Missing information",
          description: "Please fill in all required fields including SSH key paths and Hetzner Cloud API token.",
          variant: "destructive",
        });
        return;
      }
    }

    if (currentStep === 2 && !controlPlane) {
      uiToast({
        title: "Missing information",
        description: "Please complete node configuration before continuing.",
        variant: "destructive",
      });
      return;
    }

    if (currentStep === 3 && useDomainName && !domainName.trim()) {
      uiToast({
        title: "Missing Domain",
        description: "Please enter a valid domain name.",
        variant: "destructive",
      });
      return;
    }

    if (currentStep === 4) {
      // Validate Traefik credentials if enabled
      if (additionalComponents.traefik_dashboard.enabled) {
        if (!additionalComponents.traefik_dashboard.username.trim() || additionalComponents.traefik_dashboard.username.length < 3 || additionalComponents.traefik_dashboard.username.length > 20) {
          uiToast({
            title: "Invalid Username",
            description: "Traefik dashboard username must be between 3 and 20 characters.",
            variant: "destructive",
          });
          return;
        }

        if (!additionalComponents.traefik_dashboard.password.trim() || additionalComponents.traefik_dashboard.password.length < 4 || additionalComponents.traefik_dashboard.password.length > 20) {
          uiToast({
            title: "Invalid Password",
            description: "Traefik dashboard password must be between 4 and 20 characters.",
            variant: "destructive",
          });
          return;
        }
      }
    }

    setCurrentStep(currentStep + 1);
  };

  const prevStep = () => {
    setCurrentStep(currentStep - 1);
  };

  const handleSubmit = async () => {
    if (!selectedProvider || !controlPlane) {
      uiToast({
        title: "Missing information",
        description: "Please complete all required sections before creating the cluster.",
        variant: "destructive",
      });
      return;
    }

    if (selectedProvider.id === "hetzner" && (!sshPrivateKeyPath || !sshPublicKeyPath || !providerApiToken)) {
      uiToast({
        title: "Missing information",
        description: "Please provide SSH key paths and Hetzner Cloud API token.",
        variant: "destructive",
      });
      return;
    }

    // Additional validation for Traefik credentials
    if (additionalComponents.traefik_dashboard.enabled) {
      if (!additionalComponents.traefik_dashboard.username.trim() || additionalComponents.traefik_dashboard.username.length < 3 || additionalComponents.traefik_dashboard.username.length > 20) {
        uiToast({
          title: "Invalid Username",
          description: "Traefik dashboard username must be between 3 and 20 characters.",
          variant: "destructive",
        });
        return;
      }

      if (!additionalComponents.traefik_dashboard.password.trim() || additionalComponents.traefik_dashboard.password.length < 4 || additionalComponents.traefik_dashboard.password.length > 20) {
        uiToast({
          title: "Invalid Password",
          description: "Traefik dashboard password must be between 4 and 20 characters.",
          variant: "destructive",
        });
        return;
      }
    }

    setIsSubmitting(true);

    try {
      await createCluster({
        name,
        provider: selectedProvider,
        providerConfig: {
          sshPrivateKeyPath: selectedProvider.id === "hetzner" ? sshPrivateKeyPath : undefined,
          sshPublicKeyPath: selectedProvider.id === "hetzner" ? sshPublicKeyPath : undefined,
          providerApiToken:  selectedProvider.id === "hetzner" ? providerApiToken : undefined
        },
        version,
        access_ip: "Not available yet",
        controlPlane,
        nodePools,
        domainName: useDomainName ? domainName : null,
        additionalComponents: additionalComponents
      });

      uiToast({
        title: "Cluster creation started",
        description: `Your cluster "${name}" is being created. This may take a few minutes.`,
      });

      toast.success(`Cluster "${name}" creation started`, {
        description: "This may take a few minutes to complete."
      });

      onClose();
    } catch (error) {
      console.error("Failed to create cluster:", error);
      uiToast({
        title: "Failed to create cluster",
        description: error instanceof Error ? error.message : "An unknown error occurred",
        variant: "destructive",
      });
      toast.error("Failed to create cluster", {
        description: error instanceof Error ? error.message : "An unknown error occurred"
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Updated cost calculations using the unified utility functions
  const estimatedCost = selectedProvider && controlPlane
    ? (() => {
        const hasAutoscaling = nodePools.some(pool => pool.autoscaling?.enabled);
        if (hasAutoscaling) {
          return calculateClusterCostRange(controlPlane, nodePools);
        } else {
          const singleCost = calculateClusterEstimatedCost(controlPlane, nodePools);
          return {
            min: singleCost,
            max: singleCost
          };
        }
      })()
    : {
        min: { hourly: 0, monthly: 0 },
        max: { hourly: 0, monthly: 0 }
      };

  const availableNodeTypes = selectedProvider
    ? selectedProvider.nodeTypes
    : [];

  const renderNodeCountWarning = () => {
    if (showNodeCountWarning) {
      return (
        <Alert variant="warning" className="mb-4">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Node Count Warning</AlertTitle>
          <AlertDescription>
            You have configured {totalNodeCount} nodes in total, which exceeds the default Hetzner limit of {MAX_NODES_WARNING} servers.
            You may need to raise a support ticket with Hetzner to increase this limit before deployment.
          </AlertDescription>
        </Alert>
      );
    }
    return null;
  };

  const renderNoWorkerPoolWarning = () => {
    if (nodePools.length === 0) {
      return (
        <Alert variant="warning" className="mb-4">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>No Worker Pools Warning</AlertTitle>
          <AlertDescription>
            You have no worker node pools configured. This means only the control plane node will be available,
            which is not recommended for production workloads as it limits where applications can be scheduled.
          </AlertDescription>
        </Alert>
      );
    }
    return null;
  };

  const getVersionLabel = (value: string) => {
    const version = k3sVersions.find(v => v.value === value);
    return version ? version.label : value;
  };

  const renderHetznerConfigFields = () => {
    if (selectedProvider?.id !== "hetzner") return null;

    return (
      <>
        <div className="border rounded-lg p-4 space-y-4 mt-4">
          <h3 className="font-medium">Hetzner Cloud Configuration</h3>
          <div>
            <Label htmlFor="hetzner-token" className="mb-2 block">
              Hetzner Cloud API Token
            </Label>
            <Input
              id="provider-api-token"
              value={providerApiToken}
              onChange={(e) => setProviderApiToken(e.target.value)}
              type="password"
              placeholder="Enter your Hetzner Cloud API token"
              className="mb-1"
            />
            <p className="text-xs text-muted-foreground">
              The API token used to create resources in your Hetzner Cloud account
            </p>
          </div>
        </div>

        <div className="border rounded-lg p-4 space-y-4 mt-4">
          <h3 className="font-medium">SSH Key Configuration</h3>
          <div>
            <Label htmlFor="ssh-private-key" className="mb-2 block">
              SSH Private Key Path
            </Label>
            <Input
              id="ssh-private-key"
              value={sshPrivateKeyPath}
              onChange={handlePrivateKeyPathChange}
              placeholder="~/.ssh/id_rsa"
              className="mb-1"
            />
            <p className="text-xs text-muted-foreground">
              Path to your SSH private key file on your local machine
            </p>
          </div>

          <div>
            <Label htmlFor="ssh-public-key" className="mb-2 block">
              SSH Public Key Path
            </Label>
            <Input
              id="ssh-public-key"
              value={sshPublicKeyPath}
              onChange={(e) => setSshPublicKeyPath(e.target.value)}
              placeholder="~/.ssh/id_rsa.pub"
              className="mb-1"
            />
            <p className="text-xs text-muted-foreground">
              Path to your SSH public key file on your local machine
            </p>
          </div>
        </div>
      </>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent
        className="sm:max-w-[600px] overflow-y-auto max-h-[85vh]"
        ref={dialogContentRef}
      >
        <DialogHeader>
          <DialogTitle>Create a New Kubernetes Cluster</DialogTitle>
          <DialogDescription>
            Configure your new cluster for data engineering workloads.
          </DialogDescription>
        </DialogHeader>

        <div>
          <StepProgress steps={steps} currentStep={currentStep} />

          {currentStep === 1 && (
            <div className="space-y-4 py-2 animate-fade-in">
              <div>
                <Label htmlFor="name" className="mb-2 block">
                  Cluster Name
                </Label>
                <Input
                  id="name"
                  value={name}
                  onChange={handleNameChange}
                  placeholder="e.g., production-data-cluster"
                  className={`mb-1 ${nameError ? 'border-red-500 focus:border-red-500' : ''}`}
                />
                {nameError ? (
                  <p className="text-xs text-red-500 mt-1 flex items-center">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    {nameError}
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    A unique name to identify your cluster
                  </p>
                )}
              </div>

              <div>
                <Label className="mb-2 block">Cloud Provider</Label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {providers.map((provider) => (
                    <div
                      key={provider.id}
                      className={`modal-selectable-item p-4 border-2 ${
                        selectedProvider?.id === provider.id 
                          ? "border-k8s-blue bg-k8s-light/20" 
                          : "border-transparent"
                      }`}
                      onClick={() => handleProviderSelect(provider)}
                    >
                      <div className="flex items-center justify-center mb-3">
                        <img
                          src={provider.logo}
                          alt={provider.name}
                          className="h-8 object-contain"
                        />
                      </div>
                      <h3 className="text-center font-medium text-sm">
                        {provider.name}
                      </h3>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <Label htmlFor="version" className="mb-2 block">
                  k3s Version
                </Label>
                <Select value={version} onValueChange={setVersion}>
                  <SelectTrigger id="version">
                    <SelectValue placeholder="Select a version" />
                  </SelectTrigger>
                  <SelectContent>
                    {k3sVersions.map((version) => (
                      <SelectItem key={version.value} value={version.value}>
                        {version.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground mt-1">
                  k3s is a lightweight Kubernetes distribution that includes the specific Kubernetes version
                </p>
              </div>

              {renderHetznerConfigFields()}
            </div>
          )}

          {currentStep === 2 && selectedProvider && (
            <div className="space-y-6 py-2 animate-fade-in">
              <div className="border rounded-lg p-4">
                <h3 className="font-medium mb-4">Control Plane Configuration</h3>

                <div className="space-y-4">
                  <div>
                    <Label htmlFor="control-plane-region" className="mb-2 block">
                      Region
                    </Label>
                    <Select
                      onValueChange={(value) => handleControlPlaneRegionSelect(value)}
                      value={controlPlane?.region?.id || ""}
                    >
                      <SelectTrigger id="control-plane-region">
                        <SelectValue placeholder="Select a region" />
                      </SelectTrigger>
                      <SelectContent>
                        {selectedProvider.regions.map((region) => (
                          <SelectItem key={region.id} value={region.id}>
                            <div className="flex items-center">
                              <span className="text-lg mr-2">{region.flag}</span>
                              <span>{region.name}, {region.location}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="mb-2 block">Node Type</Label>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {availableNodeTypes.map((nodeType) => (
                        <div
                          key={nodeType.id}
                          className={`modal-selectable-item p-4 border-2 ${
                            controlPlane?.nodeType.id === nodeType.id 
                              ? "border-k8s-blue bg-k8s-light/20" 
                              : "border-transparent"
                          }`}
                          onClick={() =>
                            handleControlPlaneNodeTypeSelect(nodeType.id)
                          }
                        >
                          <div className="flex justify-between">
                            <div>
                              <h4 className="font-medium">{nodeType.name}</h4>
                              <p className="text-xs text-muted-foreground">
                                {nodeType.description}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-sm font-medium">
                                {nodeType.hourlyCost} €/hr
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="control-plane-count" className="mb-2 block">
                      Node Count
                    </Label>
                    <div className="flex items-center">
                      <Input
                        id="control-plane-count"
                        type="number"
                        value="1"
                        disabled
                        className="w-20 mx-2 text-center"
                      />
                      <p className="ml-4 text-sm text-muted-foreground">
                        Fixed at 1 control plane node
                      </p>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 flex items-center">
                      <Info className="h-3 w-3 mr-1" />
                      Currently, only single control plane node is supported
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium">Worker Node Pools</h3>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleAddNodePool}
                  disabled={nodePools.length >= 5}
                >
                  <Plus className="mr-2 h-4 w-4" /> Add Pool
                </Button>
              </div>

              <p className="text-sm text-muted-foreground mb-2">
                Configure the worker node pools for your Kubernetes cluster.
              </p>

              {renderNoWorkerPoolWarning()}

              <div className="space-y-4">
                {nodePools.map((pool) => (
                  <div key={pool.id} className="border rounded-lg p-4">
                    <div className="flex justify-between items-center mb-4">
                      <div className="flex items-center">
                        <Label htmlFor={`pool-name-${pool.id}`} className="mr-2">
                          Pool Name:
                        </Label>
                        <Input
                          id={`pool-name-${pool.id}`}
                          value={pool.name}
                          onChange={(e) =>
                            handleNodePoolNameChange(pool.id, e.target.value)
                          }
                          className="max-w-[200px]"
                        />
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemoveNodePool(pool.id)}
                      >
                        <Trash className="h-4 w-4 text-muted-foreground" />
                      </Button>
                    </div>

                    <div className="space-y-4">
                      <div>
                        <Label htmlFor={`pool-region-${pool.id}`} className="mb-2 block">
                          Region
                        </Label>
                        <Select
                          onValueChange={(value) => handleNodePoolRegionSelect(pool.id, value)}
                          value={pool.region?.id || ""}
                        >
                          <SelectTrigger id={`pool-region-${pool.id}`}>
                            <SelectValue placeholder="Select a region" />
                          </SelectTrigger>
                          <SelectContent>
                            {selectedProvider.regions.map((region) => (
                              <SelectItem key={region.id} value={region.id}>
                                <div className="flex items-center">
                                  <span className="text-lg mr-2">{region.flag}</span>
                                  <span>{region.name}, {region.location}</span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <Label className="mb-2 block">Node Type</Label>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {availableNodeTypes.map((nodeType) => (
                            <div
                              key={nodeType.id}
                              className={`modal-selectable-item p-4 border-2 ${
                                pool.nodeType.id === nodeType.id 
                                  ? "border-k8s-blue bg-k8s-light/20" 
                                  : "border-transparent"
                              }`}
                              onClick={() =>
                                handleNodeTypeSelect(pool.id, nodeType.id)
                              }
                            >
                              <div className="flex justify-between items-start">
                                <div>
                                  <h4 className="font-medium">{nodeType.name}</h4>
                                  <p className="text-xs text-muted-foreground">
                                    {nodeType.description}
                                  </p>
                                </div>
                                <div className="text-right">
                                  <p className="text-sm font-medium">
                                    {nodeType.hourlyCost} €/hr
                                  </p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between items-center mb-2">
                          <Label htmlFor={`node-count-${pool.id}`} className="block">
                            Node Count
                          </Label>

                          <div className="flex items-center space-x-2">
                            <Label htmlFor={`autoscaling-toggle-${pool.id}`} className="text-sm">
                              Enable Autoscaling
                            </Label>
                            <Switch
                              id={`autoscaling-toggle-${pool.id}`}
                              checked={pool.autoscaling?.enabled || false}
                              onCheckedChange={(checked) => handleAutoscalingToggle(pool.id, checked)}
                            />
                          </div>
                        </div>

                        {!pool.autoscaling?.enabled ? (
                          <div className="flex items-center">
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() =>
                                handleNodeCountChange(pool.id, pool.count - 1)
                              }
                              disabled={pool.count <= 1}
                            >
                              -
                            </Button>
                            <Input
                              id={`node-count-${pool.id}`}
                              type="number"
                              min="1"
                              max="20"
                              value={pool.count}
                              onChange={(e) =>
                                handleNodeCountChange(
                                  pool.id,
                                  parseInt(e.target.value) || 1
                                )
                              }
                              className="w-20 mx-2 text-center"
                            />
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() =>
                                handleNodeCountChange(pool.id, pool.count + 1)
                              }
                              disabled={pool.count >= 20}
                            >
                              +
                            </Button>
                            <p className="ml-4 text-sm text-muted-foreground">
                              {(pool.nodeType.hourlyCost * pool.count * 24 * 30).toFixed(2)} €/month
                            </p>
                          </div>
                        ) : (
                          <div className="space-y-3 border rounded-md p-3 bg-muted/30">
                            <div className="flex justify-between items-center">
                              <div className="flex items-center">
                                <Label htmlFor={`min-nodes-${pool.id}`} className="w-24 text-sm">
                                  Min Nodes:
                                </Label>
                                <Input
                                  id={`min-nodes-${pool.id}`}
                                  type="number"
                                  min="0"
                                  max="10"
                                  value={pool.autoscaling?.minNodes ?? 0}
                                  onChange={(e) =>
                                    handleMinNodesChange(
                                      pool.id,
                                      parseInt(e.target.value) || 0
                                    )
                                  }
                                  className="w-20 text-center"
                                />
                              </div>

                              <div className="flex items-center">
                                <Label htmlFor={`max-nodes-${pool.id}`} className="w-24 text-sm">
                                  Max Nodes:
                                </Label>
                                <Input
                                  id={`max-nodes-${pool.id}`}
                                  type="number"
                                  min="1"
                                  max="10"
                                  value={pool.autoscaling?.maxNodes ?? 1}
                                  onChange={(e) =>
                                    handleMaxNodesChange(
                                      pool.id,
                                      parseInt(e.target.value) || 1
                                    )
                                  }
                                  className="w-20 text-center"
                                />
                              </div>
                            </div>

                            {pool.autoscaling?.minNodes === 0 && (
                              <Alert variant="warning" className="mt-3">
                                <AlertTriangle className="h-4 w-4" />
                                <AlertTitle>Minimum Nodes Warning</AlertTitle>
                                <AlertDescription>
                                  Having 0 as minimum nodes can cause applications to go down from time to time as pods may not have nodes to run on. It's recommended to use at least 1 minimum node for better application availability.
                                </AlertDescription>
                              </Alert>
                            )}

                            <div className="text-sm mt-2">
                              <div className="flex justify-between items-center">
                                <span className="text-muted-foreground">Cost range:</span>
                                <span>
                                  {(pool.nodeType.hourlyCost * (pool.autoscaling?.minNodes || 0)).toFixed(4)}-{(pool.nodeType.hourlyCost * (pool.autoscaling?.maxNodes || 1)).toFixed(4)} €/hr
                                </span>
                              </div>
                              <div className="flex justify-between items-center">
                                <span className="text-muted-foreground">Monthly estimate:</span>
                                <span>
                                  {(pool.nodeType.hourlyCost * (pool.autoscaling?.minNodes || 0) * 24 * 30).toFixed(2)}-{(pool.nodeType.hourlyCost * (pool.autoscaling?.maxNodes || 1) * 24 * 30).toFixed(2)} €/month
                                </span>
                              </div>
                            </div>
                            <p className="text-xs text-muted-foreground mt-2 flex items-center">
                              <Info className="h-3 w-3 mr-1" />
                              Cost will vary based on actual node usage
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between px-4 py-3 bg-muted/50 rounded-lg">
                <p className="text-sm">
                  Total nodes: <span className="font-medium">{totalNodeCount}</span>
                </p>
                {estimatedCost.max.hourly > 0 && (
                  <p className="text-sm">
                    Estimated cost: <span className="font-medium">
                      {estimatedCost.min.hourly !== estimatedCost.max.hourly ?
                        `${estimatedCost.min.hourly.toFixed(4)}-${estimatedCost.max.hourly.toFixed(4)} €/hr` :
                        `${estimatedCost.max.hourly.toFixed(4)} €/hr`}
                    </span>
                  </p>
                )}
              </div>

              {renderNodeCountWarning()}
            </div>
          )}

          {currentStep === 3 && selectedProvider && controlPlane && (
            <div className="space-y-4 py-2 animate-fade-in">
              <h3 className="text-lg font-medium mb-4">Cluster Access</h3>

              <div className="space-y-6">
                <div className="flex flex-col gap-2">
                  <Label>Access Method</Label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div
                      className={`modal-selectable-item p-4 border-2 ${
                        !useDomainName ? "border-k8s-blue bg-k8s-light/20" : "border-transparent"
                      }`}
                      onClick={() => setUseDomainName(false)}
                    >
                      <div className="flex items-center gap-3">
                        <Globe className="h-5 w-5" />
                        <div>
                          <h4 className="font-medium">Cluster IP</h4>
                          <p className="text-sm text-muted-foreground">
                            Access applications using the cluster's IP address
                          </p>
                        </div>
                      </div>
                    </div>

                    <div
                      className={`modal-selectable-item p-4 border-2 ${
                        useDomainName ? "border-k8s-blue bg-k8s-light/20" : "border-transparent"
                      }`}
                      onClick={() => setUseDomainName(true)}
                    >
                      <div className="flex items-center gap-3">
                        <Link2 className="h-5 w-5" />
                        <div>
                          <h4 className="font-medium">Domain Name</h4>
                          <p className="text-sm text-muted-foreground">
                            Access applications using a custom domain
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {useDomainName && (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="domain-name">Domain Name</Label>
                      <Input
                        id="domain-name"
                        value={domainName}
                        onChange={(e) => setDomainName(e.target.value)}
                        placeholder="e.g., mydomain.com"
                      />
                      <p className="text-xs text-muted-foreground">
                        Enter your domain name without http:// or https://
                      </p>
                    </div>

                    <Alert variant="warning" className="mt-4">
                      <Info className="h-4 w-4" />
                      <AlertTitle>DNS Configuration Required</AlertTitle>
                      <AlertDescription>
                        After cluster creation, you'll need to create DNS record of type A pointing to the cluster's IP address.
                        The IP address will be available once the cluster is created.
                      </AlertDescription>
                    </Alert>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Updated additional components step */}
          {currentStep === 4 && (
            <div className="space-y-4 py-2 animate-fade-in">
              <h3 className="text-lg font-medium mb-4">Additional Components</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Enable additional components that will be installed on your cluster
              </p>

              <div className="space-y-4">
                <Card className="border rounded-lg">
                  <CardContent className="pt-6 pb-4">
                    <div className="flex justify-between items-start mb-4">
                      <div className="space-y-2 flex-1">
                        <h4 className="font-medium flex items-center">
                          <ToggleRight className="h-5 w-5 mr-2 text-primary" />
                          Traefik Dashboard
                        </h4>
                        <p className="text-sm text-muted-foreground">
                          Provides a web interface for monitoring and managing Traefik, the ingress controller for your cluster.
                        </p>
                      </div>
                      <Switch
                        checked={additionalComponents.traefik_dashboard.enabled}
                        onCheckedChange={handleTraefikToggle}
                      />
                    </div>

                    {additionalComponents.traefik_dashboard.enabled && (
                      <div className="space-y-4 mt-4 pt-4 border-t">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label htmlFor="traefik-username" className="mb-2 block">
                              Username
                            </Label>
                            <Input
                              id="traefik-username"
                              value={additionalComponents.traefik_dashboard.username}
                              onChange={(e) => handleTraefikUsernameChange(e.target.value)}
                              placeholder="admin"
                              minLength={3}
                              maxLength={20}
                            />
                            <p className="text-xs text-muted-foreground mt-1">
                              3-20 characters
                            </p>
                          </div>
                          <div>
                            <Label htmlFor="traefik-password" className="mb-2 block">
                              Password
                            </Label>
                            <Input
                              id="traefik-password"
                              type="password"
                              value={additionalComponents.traefik_dashboard.password}
                              onChange={(e) => handleTraefikPasswordChange(e.target.value)}
                              placeholder="Enter password"
                              minLength={4}
                              maxLength={20}
                            />
                            <p className="text-xs text-muted-foreground mt-1">
                              4-20 characters
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              <Alert className="bg-muted/50 border-muted mt-4">
                <Info className="h-4 w-4" />
                <AlertDescription>
                  Additional components may increase resource usage on your cluster. Make sure your cluster has sufficient resources.
                </AlertDescription>
              </Alert>
            </div>
          )}

          {currentStep === 5 && selectedProvider && controlPlane && (
            <div className="space-y-4 py-2 animate-fade-in">
              <h3 className="text-lg font-medium mb-4">Cluster Summary</h3>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Basic Information</CardTitle>
                </CardHeader>
                <CardContent className="pb-3">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Name:</span>
                      <span className="font-medium">{name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Provider:</span>
                      <div className="flex items-center">
                        <img src={selectedProvider.logo} alt={selectedProvider.name} className="h-4 mr-2" />
                        <span className="font-medium">{selectedProvider.name}</span>
                      </div>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Version:</span>
                      <span className="font-medium">{getVersionLabel(version)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {selectedProvider.id === "hetzner" && (
                <>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Hetzner Configuration</CardTitle>
                    </CardHeader>
                    <CardContent className="pb-3">
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">API Token:</span>
                        <span className="font-medium">••••••••••••••••</span>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">SSH Configuration</CardTitle>
                    </CardHeader>
                    <CardContent className="pb-3">
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Private Key:</span>
                          <span className="font-medium">{sshPrivateKeyPath}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Public Key:</span>
                          <span className="font-medium">{sshPublicKeyPath}</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </>
              )}

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Control Plane</CardTitle>
                </CardHeader>
                <CardContent className="pb-3">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Node Type:</span>
                      <span className="font-medium">{controlPlane.nodeType.name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Region:</span>
                      <div className="flex items-center">
                        <span className="text-lg mr-2">{controlPlane.region?.flag}</span>
                        <span className="font-medium">{controlPlane.region?.name}, {controlPlane.region?.location}</span>
                      </div>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Count:</span>
                      <span className="font-medium">1</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Worker Node Pools</CardTitle>
                </CardHeader>
                <CardContent className="pb-3 space-y-4">
                  {nodePools.length === 0 ? (
                    <p className="text-sm text-muted-foreground italic">No worker pools configured</p>
                  ) : (
                    nodePools.map((pool) => (
                      <div key={pool.id} className="p-3 border rounded-lg space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm font-medium">{pool.name}</span>
                        </div>
                        <Separator className="my-2" />
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Node Type:</span>
                          <span className="font-medium">{pool.nodeType.name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Region:</span>
                          <div className="flex items-center">
                            <span className="text-lg mr-2">{pool.region?.flag}</span>
                            <span className="font-medium">{pool.region?.name}, {pool.region?.location}</span>
                          </div>
                        </div>

                        {pool.autoscaling?.enabled ? (
                          <div className="space-y-1">
                            <div className="flex justify-between">
                              <span className="text-sm text-muted-foreground">Autoscaling:</span>
                              <span className="font-medium text-green-600">Enabled</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-sm text-muted-foreground">Min-Max Nodes:</span>
                              <span className="font-medium">{pool.autoscaling.minNodes} - {pool.autoscaling.maxNodes}</span>
                            </div>
                          </div>
                        ) : (
                          <div className="flex justify-between">
                            <span className="text-sm text-muted-foreground">Count:</span>
                            <span className="font-medium">{pool.count}</span>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              {/* Updated additional components summary in review step */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Additional Components</CardTitle>
                </CardHeader>
                <CardContent className="pb-3">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Traefik Dashboard:</span>
                      <span className={`font-medium ${additionalComponents.traefik_dashboard.enabled ? "text-green-600" : "text-muted-foreground"}`}>
                        {additionalComponents.traefik_dashboard.enabled ? "Enabled" : "Disabled"}
                      </span>
                    </div>
                    {additionalComponents.traefik_dashboard.enabled && (
                      <>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Username:</span>
                          <span className="font-medium">{additionalComponents.traefik_dashboard.username}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-muted-foreground">Password:</span>
                          <span className="font-medium">••••••••</span>
                        </div>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card
                className="bg-gradient-to-br from-soft-purple/40 to-soft-blue/40 border-2 border-primary/20 shadow-md"
              >
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center">
                    <Coins className="mr-2 h-5 w-5 text-primary" />
                    Cost Summary
                  </CardTitle>
                  <CardDescription>Estimated infrastructure costs</CardDescription>
                </CardHeader>
                <CardContent className="pb-3 space-y-2">
                  <div className="flex justify-between items-center bg-soft-blue/20 p-2 rounded-lg">
                    <span className="text-sm font-semibold flex items-center">
                      <Coins className="h-5 w-5 mr-2 text-primary" />
                      Total Hourly Cost
                    </span>
                    <span className="text-lg font-bold text-primary">
                      {estimatedCost.min.hourly !== estimatedCost.max.hourly ?
                        `${estimatedCost.min.hourly.toFixed(4)}-${estimatedCost.max.hourly.toFixed(4)} €/hr` :
                        `${estimatedCost.max.hourly.toFixed(4)} €/hr`}
                    </span>
                  </div>
                  <div className="flex justify-between items-center bg-soft-purple/20 p-2 rounded-lg mt-2">
                    <span className="text-sm font-semibold flex items-center">
                      <Calendar className="h-5 w-5 mr-2 text-primary" />
                      Estimated Monthly Cost
                    </span>
                    <span className="text-lg font-bold text-primary">
                      {estimatedCost.min.monthly !== estimatedCost.max.monthly ?
                        `${estimatedCost.min.monthly.toFixed(2)}-${estimatedCost.max.monthly.toFixed(2)} €/month` :
                        `${estimatedCost.max.monthly.toFixed(2)} €/month`}
                    </span>
                  </div>

                  <div className="text-xs text-muted-foreground mt-2 space-y-1">
                    <div className="flex justify-between">
                      <span>Control Plane (1 node):</span>
                      <span>{(controlPlane?.nodeType.hourlyCost * 24 * 30).toFixed(2)} €/month</span>
                    </div>
                    {nodePools.map((pool) => (
                      <div key={pool.id} className="flex justify-between">
                        <span>{pool.name} {pool.autoscaling?.enabled ?
                          `(${pool.autoscaling.minNodes}-${pool.autoscaling.maxNodes} nodes)` :
                          `(${pool.count} ${pool.count === 1 ? 'node' : 'nodes'})`}:</span>
                        {pool.autoscaling?.enabled ? (
                          <span>
                            {(pool.nodeType.hourlyCost * pool.autoscaling.minNodes * 24 * 30).toFixed(2)}-{(pool.nodeType.hourlyCost * pool.autoscaling.maxNodes * 24 * 30).toFixed(2)} €/month
                          </span>
                        ) : (
                          <span>{(pool.nodeType.hourlyCost * pool.count * 24 * 30).toFixed(2)} €/month</span>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {showNodeCountWarning && renderNodeCountWarning()}
              {renderNoWorkerPoolWarning()}
            </div>
          )}

          <DialogFooter className="mt-6">
            {currentStep > 1 && (
              <Button variant="outline" onClick={prevStep} disabled={isSubmitting}>
                Back
              </Button>
            )}
            {currentStep < 5 ? (
              <Button onClick={nextStep} disabled={nameError && currentStep === 1}>
                Next
              </Button>
            ) : (
              <Button onClick={handleSubmit} disabled={isSubmitting || nameError} className="bg-green-600 hover:bg-green-700">
                Create Cluster
              </Button>
            )}
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default CreateClusterModal;
