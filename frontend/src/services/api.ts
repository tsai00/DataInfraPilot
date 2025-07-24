import { Cluster, NodePool, Provider, Region, NodeType, Deployment, Volume, AccessEndpoint, AccessEndpointConfig, ClusterAdditionalComponents } from "@/types";
import { apiClient } from "./apiClient";
import { applications as defaultApplications } from "@/data/applications";
import { stateEnum } from "@/types/stateEnum";

/* CLUSTER API MODELS */
interface ApiNodePool {
  name: string;
  number_of_nodes: string;
  region: string,
  node_type: string;
  autoscaling?: {
    enabled: boolean,
    min_nodes: number | null,
    max_nodes: number | null
  }
}

interface ApiTraefikDashboardConfig {
  enabled: boolean;
  username?: string;
  password?: string;
}

interface ApiClusterAdditionalComponents {
  traefik_dashboard: ApiTraefikDashboardConfig;
}

export interface ClusterCreateRequest {
  name: string;
  provider: string;
  provider_config: object;
  k3s_version: string;
  domain_name?: string;
  pools: ApiNodePool[];
  additional_components?: ApiClusterAdditionalComponents;
}

interface ClusterCreateResponse {
  name: string;
  status: stateEnum;
}

interface ApiCluster extends ClusterCreateRequest {
  id: number;
  status: stateEnum;
  access_ip: string;
  error_message: string;
  created_at: string;
  deployments: ApiDeployment[];
}
/* ------------------ */


/* DEPLOYMENT API MODELS */
export interface UpdateDeploymentRequest {
  application_id: string;
  config: object;
}

export interface CreateDeploymentRequest extends UpdateDeploymentRequest {
  name: string;
  node_pool: string;
  endpoints: AccessEndpointConfig[]
  volumes: {
    name: string;
    size: number;
    volume_type: string;
  }[];
}

interface CreateDeploymentResponse {
  result: string;
  status: stateEnum;
  id: number;
}

export interface ApiDeployment {
  id: number;
  name: string;
  config: object;
  cluster_id: number;
  application_id: number;
  status: stateEnum;
  error_message?: string;
  installed_at: string;
  endpoints: AccessEndpointConfig[];
}
/* --------------------- */

/* VOLUME API MODELS */
export interface CreateVolumeRequest {
  name: string;
  size: number; // GB
  provider: string;
  region: string;
}

interface CreateVolumeResponse {
  name: string;
  status: stateEnum;
}

export interface ApiVolume {
  id: string;
  name: string;
  size: number;
  provider: string;
  region: string;
  status: stateEnum;
  error_message?: string,
  created_at: string;
  description?: string;
}
/* ------------------ */

/* CLUSTER ENDPOINTS */
export async function getClusters(): Promise<ApiCluster[]> {
  console.log("Fetching clusters...");
  try {
    const apiClusters = await apiClient.get<ApiCluster[]>('/clusters/');
    
    if (!apiClusters || !Array.isArray(apiClusters)) {
      console.warn("API returned non-array response for clusters:", apiClusters);
      return [];
    }
    
    return apiClusters;
  } catch (error) {
    console.error("Error fetching clusters:", error);
    throw error;
  }
}

export async function createCluster(payload: ClusterCreateRequest): Promise<ClusterCreateResponse> {
  return apiClient.post<ClusterCreateResponse>('/clusters/', payload);
}

export async function getCluster(clusterId: string): Promise<ApiCluster> {
  return apiClient.get<ApiCluster>(`/clusters/${clusterId}`);
}

export async function deleteCluster(clusterId: string): Promise<void> {
  return apiClient.delete(`/clusters/${clusterId}`);
}

export async function getClusterKubeconfig(clusterId: string): Promise<string> {
  return apiClient.get<string>(`/clusters/${clusterId}/kubeconfig`);
}
/* ------------------ */


/* DEPLOYMENT ENDPOINTS */
export async function createDeployment(clusterId: string, payload: CreateDeploymentRequest): Promise<CreateDeploymentResponse> {
  return apiClient.post<CreateDeploymentResponse>(`/clusters/${clusterId}/deployments`, payload);
}

export async function updateDeployment(clusterId: string, deploymentId: string, payload: UpdateDeploymentRequest): Promise<CreateDeploymentResponse> {
  return apiClient.post<CreateDeploymentResponse>(`/clusters/${clusterId}/deployments/${deploymentId}`, payload);
}

export async function deleteDeployment(clusterId: string, deploymentId: string): Promise<void> {
  return apiClient.delete(`/clusters/${clusterId}/deployments/${deploymentId}`);
}

export async function getDeploymentCredentials(clusterId: string, deploymentId: string): Promise<{ username: string; password: string }> {
  return apiClient.get<{ username: string; password: string }>(`/clusters/${clusterId}/deployments/${deploymentId}/credentials`);
}

export async function checkEndpointExistence(clusterId: string, endpointConfig: AccessEndpointConfig): Promise<boolean> {
  return apiClient.post<boolean>(`/clusters/${clusterId}/deployments/check-endpoint-existence`, endpointConfig);
}
/* -------------------- */


/* APPLICATION ENDPOINTS */
export async function getApplicationVersions(appId: string): Promise<string[]> {
  return apiClient.get<string[]>(`/applications/${appId}/versions`);
}

export async function getApplicationAccessEndpoints(appId: string): Promise<AccessEndpoint[]> {
  return apiClient.get<AccessEndpoint[]>(`/applications/${appId}/access_endpoints`);
}
/* --------------------- */


/* VOLUME ENDPOINTS */
export async function getVolumes(): Promise<ApiVolume[]> {
  try {
    const apiVolumes = await apiClient.get<ApiVolume[]>('/volumes/');
    
    if (!apiVolumes || !Array.isArray(apiVolumes)) {
      console.warn("API returned non-array response for volumes:", apiVolumes);
      return [];
    }
    
    return apiVolumes;
  } catch (error) {
    console.error("Error fetching volumes:", error);
    throw error;
  }
}

export async function createVolume(payload: CreateVolumeRequest): Promise<CreateVolumeResponse> {
  return apiClient.post<CreateVolumeResponse>('/volumes/', payload);
}

export async function deleteVolume(volumeId: string): Promise<void> {
  return apiClient.delete(`/volumes/${volumeId}`);
}
/* ------------------ */


// Helper function to convert between API and UI models
export function mapApiClusterToUICluster(apiCluster: ApiCluster, providers: Provider[]): Cluster {
  if (!apiCluster || typeof apiCluster !== 'object') {
    console.warn('Invalid cluster data received from API:', apiCluster);
    throw new Error('Invalid cluster data received from API');
  }

  console.log('Fetched cluster deployments: ' + JSON.stringify(apiCluster.deployments))

  const provider = providers.find(p => p.id === apiCluster.provider);

  const workerPools = apiCluster.pools.slice(1);
  
  // Get nodeTypes from our provider
  const nodeTypes = getNodeTypesFromProvider(provider);
    
  const nodePools: NodePool[] = apiCluster.pools.map((pool: ApiNodePool) => {
    // Find matching nodeType or use default
    const nodeTypeId = typeof pool.node_type === 'string' ? pool.node_type : 'default';
    
    // Find nodeType by id string
    const nodeType = nodeTypes.find(nt => nt.id === nodeTypeId);
    
    return {
      id: `pool-${Math.random().toString(36).substring(2, 9)}`,
      name: pool.name,
      nodeType: nodeType,
      count: parseInt(pool.number_of_nodes),
      region: provider.regions.find(r => r.id === pool.region),
      autoscaling: pool.autoscaling ? {
        enabled: pool.autoscaling.enabled,
        minNodes: pool.autoscaling.min_nodes,
        maxNodes: pool.autoscaling.max_nodes
      } : null
    };
  });

  const deployments: Deployment[] = apiCluster.deployments.map((deployment) => {
    return {
      id: deployment.id.toString(),
      name: deployment.name,
      application: defaultApplications.find(a => a.id === deployment.application_id),
      status: deployment.status,
      config: deployment.config,
      errorMessage: deployment.error_message,
      deployedAt: deployment.installed_at,
      accessEndpoints: deployment.endpoints
    }
  });

  const additionalComponents: ClusterAdditionalComponents = {
    traefik_dashboard: {
      enabled: apiCluster.additional_components?.traefik_dashboard?.enabled || false,
      username: apiCluster.additional_components?.traefik_dashboard?.username || '',
      password: apiCluster.additional_components?.traefik_dashboard?.password || ''
    },
  }

  return {
    id: apiCluster.id.toString(),
    name: apiCluster.name,
    access_ip: apiCluster.access_ip,
    domainName: apiCluster.domain_name,
    errorMessage: apiCluster.error_message,
    provider: provider,
    providerConfig: apiCluster.provider_config,
    version: apiCluster.k3s_version,
    controlPlane: nodePools[0],
    nodePools: nodePools.slice(1),
    status: apiCluster.status,
    created: apiCluster.created_at || new Date().toISOString(),
    deployments: deployments,
    additionalComponents: additionalComponents
  };
}

// Map API volume to UI volume
export function mapApiVolumeToUIVolume(apiVolume: ApiVolume): Volume {
  return {
    id: apiVolume.id,
    name: apiVolume.name,
    size: apiVolume.size,
    provider: apiVolume.provider,
    region: apiVolume.region,
    status: apiVolume.status,
    createdAt: apiVolume.created_at,
    description: apiVolume.description,
  };
}

// Helper function to handle getting node types safely
function getNodeTypesFromProvider(provider: Provider): NodeType[] {
  if ('nodeTypes' in provider && Array.isArray((provider as any).nodeTypes)) {
    return (provider as any).nodeTypes;
  }
  return [];
}

// Helper function to download a file
export function downloadFile(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
