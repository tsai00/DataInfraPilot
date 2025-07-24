
import { stateEnum } from "./stateEnum";

export type Provider = {
  id: string;
  name: string;
  logo: string;
  description: string;
  regions: Region[];
  volumeCostGbPerHour: number,
  nodeTypes: NodeType[];
};

export type Region = {
  id: string;
  name: string;
  location: string;
  flag: string;
};

export type NodeType = {
  id: string;
  name: string;
  cpu: number;
  memory: number;
  description: string;
  hourlyCost: number;
};

export type NodePool = {
  id: string;
  name: string;
  nodeType: NodeType;
  count: number;
  region?: Region;
  autoscaling?: {
    enabled: boolean;
    minNodes: number;
    maxNodes: number;
  };
};

export type TraefikDashboardConfig = {
  enabled: boolean;
  username: string;
  password: string;
};

export type ClusterAdditionalComponents = {
  traefik_dashboard: TraefikDashboardConfig;
}

export type Cluster = {
  id: string;
  name: string;
  access_ip: string,
  errorMessage?: string,
  provider: Provider;
  providerConfig: object;
  version: string;
  controlPlane: NodePool;
  nodePools: NodePool[];
  status: stateEnum;
  domainName?: string;
  created: string;
  deployments: Deployment[];
  additionalComponents?: ClusterAdditionalComponents;
};

export type Application = {
  id: number;
  short_name: string;
  name: string;
  description: string;
  logo: string;
  configOptions: ConfigOption[];
  versions?: string[];
  volumeRequirements?: VolumeRequirement[];
  recommendedResources?: {
    nodes: string;
    ram: string;
    cpu: string;
  };
};

export type VolumeRequirement = {
  id: string;
  name: string;
  description: string;
  defaultSize: number; // in GB
}

export type Volume = {
  id: string;
  name: string;
  size: number; // in GB
  provider: string;
  region: string;
  status: stateEnum;
  createdAt: string;
  description?: string;
  inUse?: boolean;
};

export enum AccessEndpointType {
  SUBDOMAIN = "subdomain",
  DOMAIN_PATH = "domain_path",
  CLUSTER_IP_PATH = "cluster_ip_path"
}

export type AccessEndpoint = {
  name: string;
  description: string;
  default_access: AccessEndpointType;
  default_value: string;
  required: boolean;
};

export type AccessEndpointConfig = {
  name: string;
  access_type: AccessEndpointType;
  value: string;
};


export type ConfigOption = {
  id: string;
  name: string;
  type: "text" | "number" | "select" | "boolean";
  description: string;
  required: boolean;
  default?: string | number | boolean;
  options?: { value: string; label: string }[];
  applicationId?: number;
  conditional?: {
    field: string;
    value: any;
  };
};

export type Deployment = {
  id: number;
  name: string;
  application: Application;
  status: stateEnum;
  config: Record<string, any>;
  deployedAt: string;
  nodePool?: string;
  volumes?: DeploymentVolume[];
  errorMessage?: string,
  accessEndpoints?: AccessEndpointConfig[];
};

export type DeploymentVolume = {
  volumeName: string;
};

export interface DomainActivity {
  id: string;
  domainName: string;
  action: "added" | "verified" | "deleted" | "creating" | "deleting" | "deploying" | "deployed" | "removed" | "updating";
  timestamp: string;
}
