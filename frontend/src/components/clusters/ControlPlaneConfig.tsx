import React from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Info } from "lucide-react";
import { Provider, NodePool, NodeType } from "@/types";

interface ControlPlaneConfigProps {
  provider: Provider;
  controlPlane: NodePool | null;
  onRegionSelect: (regionId: string) => void;
  onNodeTypeSelect: (nodeTypeId: string) => void;
  showManagedInfo?: boolean;
}

const ControlPlaneConfig: React.FC<ControlPlaneConfigProps> = ({
  provider,
  controlPlane,
  onRegionSelect,
  onNodeTypeSelect,
  showManagedInfo = false,
}) => {
  if (showManagedInfo) {
    return (
      <div className="border rounded-lg p-4">
        <h3 className="font-medium mb-4">Control Plane Configuration</h3>
        <Alert className="mb-4">
          <Info className="h-4 w-4" />
          <AlertTitle>Managed Control Plane</AlertTitle>
          <AlertDescription>
            DigitalOcean Kubernetes uses a fully managed control plane.
            The control plane nodes are automatically managed and maintained by DigitalOcean.
          </AlertDescription>
        </Alert>

        <div>
          <Label htmlFor="control-plane-region" className="mb-2 block">
            Cluster Region
          </Label>
          <Select
            onValueChange={onRegionSelect}
            value={controlPlane?.region?.id || ""}
          >
            <SelectTrigger id="control-plane-region">
              <SelectValue placeholder="Select a region" />
            </SelectTrigger>
            <SelectContent>
              {provider.regions.map((region) => (
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
      </div>
    );
  }

  return (
    <div className="border rounded-lg p-4">
      <h3 className="font-medium mb-4">Control Plane Configuration</h3>

      <div className="space-y-4">
        <div>
          <Label htmlFor="control-plane-region" className="mb-2 block">
            Region
          </Label>
          <Select
            onValueChange={onRegionSelect}
            value={controlPlane?.region?.id || ""}
          >
            <SelectTrigger id="control-plane-region">
              <SelectValue placeholder="Select a region" />
            </SelectTrigger>
            <SelectContent>
              {provider.regions.map((region) => (
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
            {provider.nodeTypes.map((nodeType) => (
              <div
                key={nodeType.id}
                className={`modal-selectable-item p-4 border-2 ${
                  controlPlane?.nodeType.id === nodeType.id 
                    ? "border-k8s-blue bg-k8s-light/20" 
                    : "border-transparent"
                }`}
                onClick={() => onNodeTypeSelect(nodeType.id)}
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
                      {nodeType.hourlyCost} {provider.id === 'hetzner' ? '€' : '$'}/hr
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
  );
};

export default ControlPlaneConfig;