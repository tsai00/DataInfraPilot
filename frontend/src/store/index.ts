
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { v4 as uuidv4 } from "uuid";
import { 
  Cluster, 
  Provider, 
  Region, 
  NodeType, 
  NodePool, 
  Application, 
  Deployment,
  DomainActivity,
  Volume,
  DeploymentVolume,
  AccessEndpointConfig,
} from "@/types";
import { 
  clusters as mockClusters, 
  volumes as mockVolumes
} from "@/data/mockData";
import { applications } from "@/data/applications";
import * as api from "@/services/api";
import { toast } from "sonner";
import { providers } from "@/data/providers";
import { stateEnum } from "@/types/stateEnum";
import { calculateNodePoolsCost } from "@/utils/costCalculations";

interface ClusterState {
  clusters: Cluster[];
  applications: Application[];
  providers: Provider[];
  domains: Array<{id: string, name: string, status: "verified" | "pending", createdAt: string}>;
  domainActivities: DomainActivity[];
  volumes: Volume[];
  
  createCluster: (cluster: Omit<Cluster, "id" | "created" | "deployments" | "status">) => Promise<void>;
  deleteCluster: (clusterId: string) => Promise<void>;
  createDeployment: (
    clusterId: string, 
    application: Application, 
    config: Record<string, any>,
    nodePool: string,
    volumes: {
      name: string;
      volume_type: string;
      size: number;
    }[],
    endpoints: AccessEndpointConfig[]
  ) => Promise<void>;
  updateDeployment: (clusterId: string, deploymentId: string, config: Record<string, any>) => Promise<void>;
  deleteDeployment: (clusterId: string, deploymentId: string) => void;
  calculateClusterCost: (
    provider: Provider,
    nodePools: NodePool[]
  ) => { hourly: number; monthly: number };
  addDomain: (domainName: string) => void;
  deleteDomain: (domainId: string) => void;
  downloadKubeconfig: (clusterId: string) => Promise<void>;
  fetchClusters: () => Promise<void>;
  
  fetchVolumes: () => Promise<void>;
  createVolume: (
    name: string,
    size: number,
    Provider: string,
    region: string
  ) => Promise<void>;
  deleteVolume: (volumeId: string) => Promise<void>;
  getAvailableVolumesForProvider: (
    providerId: string 
  ) => Volume[];
}

const initialDomains = [
  {
    id: "domain-1",
    name: "app.example.com",
    status: "verified" as const,
    createdAt: "2025-03-15T08:30:00Z",
  },
  {
    id: "domain-2",
    name: "api.example.com",
    status: "pending" as const,
    createdAt: "2025-04-05T14:22:00Z",
  }
];

const initialDomainActivities: DomainActivity[] = [
  {
    id: "act-1",
    domainName: "app.example.com",
    action: "added",
    timestamp: "2025-03-15T08:30:00Z"
  },
  {
    id: "act-2",
    domainName: "api.example.com",
    action: "added",
    timestamp: "2025-04-05T14:22:00Z"
  }
];

export const useClusterStore = create<ClusterState>()(
  persist(
    (set, get) => ({
      clusters: mockClusters,
      applications: applications,
      providers: providers,
      domains: initialDomains,
      domainActivities: initialDomainActivities,
      volumes: mockVolumes,

      fetchClusters: async () => {
        try {
          const apiClusters = await api.getClusters();
          
          const uiClusters = apiClusters.map(cluster => 
            api.mapApiClusterToUICluster(cluster, get().providers)
          );

          set({ clusters: uiClusters });
        } catch (error) {
          console.error("Failed to fetch clusters:", error);
          toast.error("Failed to fetch clusters", {
            description: error instanceof Error ? error.message : "Unknown error occurred"
          });
        }
      },

      createCluster: async (clusterData) => {
        const tempCluster: Cluster = {
          ...clusterData,
          id: uuidv4(),
          status: stateEnum.CREATING,
          created: new Date().toISOString(),
          deployments: [],
        };

        set((state) => ({
          clusters: [...state.clusters, tempCluster],
        }));

        const newActivity: DomainActivity = {
          id: `act-cluster-${Date.now()}`,
          domainName: clusterData.name,
          action: "creating",
          timestamp: new Date().toISOString()
        };
        
        set((state) => ({
          domainActivities: [newActivity, ...state.domainActivities]
        }));

        try {
          const workerPools = clusterData.nodePools.map(pool => ({
            name: pool.name,
            number_of_nodes: String(pool.autoscaling.enabled ? pool.autoscaling.minNodes : pool.count),
            node_type: pool.nodeType.id,
            region: pool.region.id,
            autoscaling: {
              enabled: pool.autoscaling.enabled,
              min_nodes: pool.autoscaling.minNodes,
              max_nodes: pool.autoscaling.maxNodes
            }
          }));
          
          const controlPlanePool = {
            name: "control-plane",
            number_of_nodes: String(clusterData.controlPlane.count),
            node_type: clusterData.controlPlane.nodeType.id,
            region: clusterData.controlPlane.region.id,
          };

          console.log("Prepated controlp plane");
          
          const allPools = [controlPlanePool, ...workerPools];
          
          const apiPayload: api.ClusterCreateRequest = {
            name: clusterData.name,
            k3s_version: clusterData.version,
            provider: clusterData.provider.id,
            provider_config: {
              api_token: clusterData.providerConfig['providerApiToken'],
              ssh_private_key_path: clusterData.providerConfig['sshPrivateKeyPath'],
              ssh_public_key_path: clusterData.providerConfig['sshPublicKeyPath'],
            },
            domain_name: clusterData.domainName,
            pools: allPools,
            additional_components: {
              traefik_dashboard: {
                enabled: clusterData.additionalComponents?.traefik_dashboard?.enabled || false,
                username: clusterData.additionalComponents?.traefik_dashboard?.username || '',
                password: clusterData.additionalComponents?.traefik_dashboard?.password || ''
              }
            }
          };

          console.log('Cluster payload ' + JSON.stringify(apiPayload));
          
          const response = await api.createCluster(apiPayload);
          
          set((state) => ({
            clusters: state.clusters.map((c) =>
              c.id === tempCluster.id 
                ? { ...c, status: response.status } 
                : c
            ),
          }));
          
          setTimeout(() => {
            get().fetchClusters();
          }, 10000);
          
        } catch (error) {
          console.error("Failed to create cluster:", error);
          
          toast.error("Failed to create cluster", {
            description: error instanceof Error ? error.message : "Unknown error occurred"
          });
          
          set((state) => ({
            clusters: state.clusters.map((c) =>
              c.id === tempCluster.id ? { ...c, status: stateEnum.FAILED } : c
            ),
          }));
        }
      },

      deleteCluster: async (clusterId) => {
        const clusterToDelete = get().clusters.find(c => c.id === clusterId);
        
        set((state) => ({
          clusters: state.clusters.map((c) =>
            c.id === clusterId ? { ...c, status: stateEnum.DELETING } : c
          ),
        }));
        
        if (clusterToDelete) {
          const newActivity: DomainActivity = {
            id: `act-cluster-delete-${Date.now()}`,
            domainName: clusterToDelete.name,
            action: "deleting",
            timestamp: new Date().toISOString()
          };
          
          set((state) => ({
            domainActivities: [newActivity, ...state.domainActivities]
          }));
        }

        try {
          await api.deleteCluster(clusterId);
          
          toast.success("Cluster deletion initiated", {
            description: "The cluster is being deleted. This may take a few minutes."
          });
          
          setTimeout(() => {
            set((state) => ({
              clusters: state.clusters.filter((c) => c.id !== clusterId),
            }));
            
            if (clusterToDelete) {
              const completionActivity: DomainActivity = {
                id: `act-cluster-deleted-${Date.now()}`,
                domainName: clusterToDelete.name,
                action: "deleted",
                timestamp: new Date().toISOString()
              };
              
              set((state) => ({
                domainActivities: [completionActivity, ...state.domainActivities]
              }));
            }
          }, 8000);
          
        } catch (error) {
          console.error("Failed to delete cluster:", error);
          
          toast.error("Failed to delete cluster", {
            description: error instanceof Error ? error.message : "Unknown error occurred"
          });
          
          set((state) => ({
            clusters: state.clusters.map((c) =>
              c.id === clusterId ? { ...c, status: stateEnum.FAILED } : c
            ),
          }));
        }
      },

      downloadKubeconfig: async (clusterId) => {
        try {
          const kubeconfig = await api.getClusterKubeconfig(clusterId);
          const cluster = get().clusters.find(c => c.id === clusterId);
          
          if (cluster) {
            api.downloadFile(kubeconfig, `${cluster.name}-kubeconfig.yaml`);
            
            toast.success("Kubeconfig downloaded", {
              description: `The kubeconfig for ${cluster.name} has been downloaded.`
            });
          }
        } catch (error) {
          console.error("Failed to download kubeconfig:", error);
          
          toast.error("Failed to download kubeconfig", {
            description: error instanceof Error ? error.message : "Unknown error occurred"
          });
          
          throw error;
        }
      },

      createDeployment: async (clusterId, application, config, nodePool, volumes = [], endpoints) => {
        const deploymentId = `deployment-${Math.random().toString(36).substring(2, 9)}`;
        const currentCluster = get().clusters.find(c => c.id === clusterId);

        const deploymentVolumes: DeploymentVolume[] = [];
        
        if (volumes && volumes.length > 0) {
          volumes.forEach(vol => {
            let volumeName = "";
            
            if (vol.name) {
              const existingVolume = get().volumes.find(v => v.name === vol.name);
              if (existingVolume) {
                volumeName = existingVolume.name;
                
                set((state) => ({
                  volumes: state.volumes.map(v => 
                    v.name === vol.name 
                      ? { ...v, inUse: true } 
                      : v
                  )
                }));
              }
            } else {
              volumeName = `${application.name.toLowerCase()}-${Math.random().toString(36).substring(2, 5)}`;
              
              const volumeRequirement = application.volumeRequirements?.find(vr => vr.name === vol.name);
              
              if (volumeRequirement && currentCluster) {
                const newVolume: Volume = {
                  id: `vol-new-${Date.now()}-${Math.random().toString(36).substring(2, 5)}`,
                  name: volumeName,
                  size: vol.size || volumeRequirement.defaultSize,
                  provider: currentCluster.provider.name,
                  region: currentCluster.controlPlane.region?.id || "",
                  status: stateEnum.CREATING,
                  createdAt: new Date().toISOString(),
                  description: volumeRequirement.description,
                  inUse: true,
                };
                
                set((state) => ({
                  volumes: [...state.volumes, newVolume]
                }));
              }
            }
            
            const volumeReq = application.volumeRequirements?.find(vr => vr.name === vol.name);
            if (volumeReq) {
              deploymentVolumes.push({
                volumeName,
              });
            }
          });
        }

        const newDeployment: Deployment = {
          id: deploymentId,
          name: config.deployment_name || `${application.name} Deployment`,
          application,
          status: stateEnum.DEPLOYING,
          config,
          deployedAt: new Date().toISOString(),
          nodePool,
          volumes: deploymentVolumes.length > 0 ? deploymentVolumes : undefined,
          accessEndpoints: endpoints
        };

        set((state) => ({
          clusters: state.clusters.map((c) =>
            c.id === clusterId
              ? {
                  ...c,
                  deployments: [...c.deployments, newDeployment],
                }
              : c
          ),
        }));

        const apiPayload: api.CreateDeploymentRequest = {
          name: config.deployment_name || `${application.name} Deployment`,
          application_id: application.id.toString(),
          config: config,
          node_pool: nodePool,
          endpoints: endpoints,
          volumes: volumes.map(vol => ({
            name: vol.name,
            volume_type: vol.volume_type,
            size: vol.size
          }))
        };
        
        try {
          const response = await api.createDeployment(clusterId, apiPayload);
          
          if (currentCluster) {
            const newActivity: DomainActivity = {
              id: `act-app-deploy-${Date.now()}`,
              domainName: `${application.name} on ${currentCluster.name}`,
              action: "deploying",
              timestamp: new Date().toISOString()
            };
            
            set((state) => ({
              domainActivities: [newActivity, ...state.domainActivities]
            }));
          }

          setTimeout(() => {
            set((state) => ({
              clusters: state.clusters.map((c) =>
                c.id === clusterId
                  ? {
                      ...c,
                      deployments: c.deployments.map((deployment) =>
                        deployment.id === newDeployment.id
                          ? {
                              ...deployment,
                              status: stateEnum.RUNNING,
                            }
                          : deployment
                      ),
                    }
                  : c
              ),
              volumes: state.volumes.map(vol => 
                vol.status === stateEnum.CREATING
                  ? { ...vol, status: stateEnum.RUNNING }
                  : vol
              )
            }));
            
            if (currentCluster) {
              const completionActivity: DomainActivity = {
                id: `act-app-deployed-${Date.now()}`,
                domainName: `${application.name} on ${currentCluster.name}`,
                action: "deployed",
                timestamp: new Date().toISOString()
              };
              
              set((state) => ({
                domainActivities: [completionActivity, ...state.domainActivities]
              }));
              
              toast.success(`${application.name} deployed`, {
                description: `The application is now running on ${currentCluster.name}.`
              });
            }
          }, 15000);
        } catch (error) {
          console.error("Failed to create deployment:", error);
          toast.error("Failed to create deployment", {
            description: error instanceof Error ? error.message : "Unknown error occurred"
          });
        }
      },

      updateDeployment: async (clusterId, deploymentId, config) => {
        const cluster = get().clusters.find(c => c.id === clusterId);
        const deployment = cluster?.deployments.find(d => d.id === deploymentId);

        if (!deployment) {
          console.error("Deployment not found");
          toast.error("Deployment not found");
          return;
        }

        const apiPayload: api.UpdateDeploymentRequest = {
          application_id: deployment.application.id.toString(),
          config: config
        };
        
        try {
          const response = await api.updateDeployment(clusterId, deploymentId, apiPayload);
          
          if (cluster) {
            const newActivity: DomainActivity = {
              id: `act-app-deploy-${Date.now()}`,
              domainName: `${deployment.application.name} on ${cluster.name}`,
              action: "updating",
              timestamp: new Date().toISOString()
            };
            
            set((state) => ({
              domainActivities: [newActivity, ...state.domainActivities]
            }));
          }

          setTimeout(() => {
            set((state) => ({
              clusters: state.clusters.map((c) =>
                c.id === clusterId
                  ? {
                      ...c,
                      deployments: c.deployments.map((deployment) =>
                        deployment.id === deploymentId
                          ? {
                              ...deployment,
                              name: config.deployment_name || deployment.name,
                              config,
                              status: stateEnum.RUNNING,
                            }
                          : deployment
                      ),
                    }
                  : c
              ),
            }));
            
            if (cluster) {
              const completionActivity: DomainActivity = {
                id: `act-app-deployed-${Date.now()}`,
                domainName: `${deployment.application.name} on ${cluster.name}`,
                action: "deployed",
                timestamp: new Date().toISOString()
              };
              
              set((state) => ({
                domainActivities: [completionActivity, ...state.domainActivities]
              }));
              
              toast.success(`${deployment.application.name} updated`, {
                description: `The application has been updated on ${cluster.name}.`
              });
            }
          }, 15000);
        } catch (error) {
          console.error("Failed to update deployment:", error);
          toast.error("Failed to update deployment", {
            description: error instanceof Error ? error.message : "Unknown error occurred"
          });
        }
      },

      deleteDeployment: async (clusterId, deploymentId) => {
        const cluster = get().clusters.find(c => c.id === clusterId);
        const deployment = cluster?.deployments.find(d => d.id === deploymentId);
        
        if (!deployment) {
          console.error("Deployment not found");
          toast.error("Deployment not found");
          return;
        }

        set((state) => ({
          clusters: state.clusters.map((c) =>
            c.id === clusterId
              ? {
                  ...c,
                  deployments: c.deployments.filter((d) => d.id !== deploymentId),
                }
              : c
          ),
        }));
        
        if (cluster && deployment) {
          try {
            await api.deleteDeployment(clusterId, deploymentId);
            
            toast.success("Application uninstallation started", {
              description: "The application is being uninstalled. This may take a few minutes."
            });
            
          } catch (error) {
            console.error("Failed to uninstall application:", error);
            
            toast.error("Failed to uninstall application", {
              description: error instanceof Error ? error.message : "Unknown error occurred"
            });
            
            get().fetchClusters();
          }

          const newActivity: DomainActivity = {
            id: `act-app-remove-${Date.now()}`,
            domainName: `${deployment.application.name} from ${cluster.name}`,
            action: "removed",
            timestamp: new Date().toISOString()
          };
          
          set((state) => ({
            domainActivities: [newActivity, ...state.domainActivities]
          }));
          
          toast.success(`${deployment.application.name} removed`, {
            description: `The application has been removed from ${cluster.name}.`
          });
        }
      },

      calculateClusterCost: (
        provider: Provider,
        nodePools: NodePool[]
      ) => {
        const cost = calculateNodePoolsCost(nodePools);
        return cost;
      },

      addDomain: (domainName) => {
        const newDomain = {
          id: `domain-${Date.now()}`,
          name: domainName,
          status: "pending" as const,
          createdAt: new Date().toISOString(),
        };
        
        const newActivity: DomainActivity = {
          id: `act-${Date.now()}`,
          domainName: domainName,
          action: "added",
          timestamp: new Date().toISOString()
        };
        
        set((state) => ({
          domains: [...state.domains, newDomain],
          domainActivities: [newActivity, ...state.domainActivities]
        }));
        
        setTimeout(() => {
          set((state) => ({
            domains: state.domains.map(d => 
              d.id === newDomain.id 
                ? { ...d, status: "verified" as const } 
                : d
            ),
            domainActivities: [{
              id: `act-${Date.now()}`,
              domainName: domainName,
              action: "verified",
              timestamp: new Date().toISOString()
            }, ...state.domainActivities]
          }));
          
          toast.success(`Domain ${domainName} verified`, {
            description: "The domain has been successfully verified."
          });
        }, 5000);
      },
      
      deleteDomain: (domainId) => {
        const domainToDelete = get().domains.find(d => d.id === domainId);
        
        if (domainToDelete) {
          const newActivity: DomainActivity = {
            id: `act-${Date.now()}`,
            domainName: domainToDelete.name,
            action: "deleted",
            timestamp: new Date().toISOString()
          };
          
          set((state) => ({
            domains: state.domains.filter(d => d.id !== domainId),
            domainActivities: [newActivity, ...state.domainActivities]
          }));
          
          toast.success(`Domain ${domainToDelete.name} deleted`, {
            description: "The domain has been successfully removed."
          });
        }
      },
      
      fetchVolumes: async () => {
        try {
          const apiVolumes = await api.getVolumes();
          
          const uiVolumes = apiVolumes.map(vol => 
            api.mapApiVolumeToUIVolume(vol)
          );

          set({ volumes: uiVolumes });
        } catch (error) {
          console.error("Failed to fetch volumes:", error);
          toast.error("Failed to fetch volumes", {
            description: error instanceof Error ? error.message : "Unknown error occurred"
          });
        }
      },
      
      createVolume: async (name, size, provider, region) => {
        const tempVolume: Volume = {
          id: `temp-vol-${Date.now()}`,
          name,
          size,
          provider,
          region,
          status: stateEnum.CREATING,
          createdAt: new Date().toISOString()
        };
        
        set((state) => ({
          volumes: [...state.volumes, tempVolume]
        }));
        
        try {
          const payload: api.CreateVolumeRequest = {
            name,
            size,
            provider: provider,
            region: region
          };
          
          const response = await api.createVolume(payload);
          
          setTimeout(() => {
            set((state) => ({
              volumes: state.volumes.map(vol => 
                vol.id === tempVolume.id 
                  ? { ...vol, status: response.status } 
                  : vol
              )
            }));
            
            toast.success(`Volume "${name}" created`, {
              description: `The ${size}GB volume has been successfully created.`
            });
          }, 3000);
          
        } catch (error) {
          console.error("Failed to create volume:", error);
          
          toast.error("Failed to create volume", {
            description: error instanceof Error ? error.message : "Unknown error occurred"
          });
          
          set((state) => ({
            volumes: state.volumes.filter(vol => vol.id !== tempVolume.id)
          }));
        }
      },
      
      deleteVolume: async (volumeId) => {
        const volumeToDelete = get().volumes.find(v => v.id === volumeId);
        
        if (!volumeToDelete) {
          toast.error("Volume not found");
          return;
        }
        
        set((state) => ({
          volumes: state.volumes.map(vol => 
            vol.id === volumeId 
              ? { ...vol, status: stateEnum.DELETING } 
              : vol
          )
        }));
        
        try {
          await api.deleteVolume(volumeId);
          
          setTimeout(() => {
            set((state) => ({
              volumes: state.volumes.filter(vol => vol.id !== volumeId)
            }));
            
            toast.success(`Volume "${volumeToDelete.name}" deleted`, {
              description: "The volume has been successfully removed."
            });
          }, 3000);
          
        } catch (error) {
          console.error("Failed to delete volume:", error);
          
          toast.error("Failed to delete volume", {
            description: error instanceof Error ? error.message : "Unknown error occurred"
          });
          
          set((state) => ({
            volumes: state.volumes.map(vol => 
              vol.id === volumeId 
                ? { ...vol, status: stateEnum.RUNNING } 
                : vol
            )
          }));
        }
      },
      
      getAvailableVolumesForProvider: (providerId) => {
        const provider = get().providers.find(p => p.id === providerId);
        
        if (!provider) return [];
        
        return get().volumes.filter(vol => 
          vol.provider === provider.id && 
          vol.status === stateEnum.RUNNING
        );
      }
    }),
    {
      name: "clustercraft-storage",
    }
  )
);

setTimeout(() => {
  useClusterStore.getState().fetchClusters();
  useClusterStore.getState().fetchVolumes();
}, 1000);
