
import { Cluster, Deployment, Provider, Region, Application, NodePool, Volume } from "@/types";
import { providers } from "@/data/providers";
import { stateEnum } from "@/types/stateEnum";
import { v4 as uuidv4 } from 'uuid';
import { applications } from "@/data/applications";

export const clusters: Cluster[] = [
  {
    id: "cluster-1",
    name: "production-data-cluster",
    access_ip: "1.2.3.4",
    provider: providers[0],
    providerConfig: {}, // Added the missing providerConfig property
    version: "1.26.1",
    domainName: "exampledomain.com",
    controlPlane: {
      id: "control-plane-pool",
      name: "control-plane",
      nodeType: providers[0].nodeTypes[0],
      count: 1,
      region: providers[0].regions[0]
    },
    nodePools: [
      {
        id: "pool-1",
        name: "worker-pool",
        nodeType: providers[0].nodeTypes[1],
        count: 3,
        region: providers[0].regions[0]
      },
      {
        id: "pool-2",
        name: "data-pool",
        nodeType: providers[0].nodeTypes[2],
        count: 2,
        region: providers[0].regions[0]
      },
    ],
    status: stateEnum.RUNNING,
    created: "2023-09-15T09:00:00Z",
    deployments: [
      {
        id: "app-1",
        name: "Airflow Deployment", 
        application: applications[0],
        status: stateEnum.RUNNING,
        config: {
          executor: "KubernetesExecutor",
          workers: 3,
          enable_ssl: true,
        },
        deployedAt: "2023-09-16T14:30:00Z",
      },
    ],
  },
  {
    id: "cluster-2",
    name: "staging-ml-cluster",
    access_ip: "1.2.3.4",
    provider: providers[0],
    providerConfig: {}, // Added the missing providerConfig property
    version: "1.25.0",
    controlPlane: {
      id: "control-plane-pool",
      name: "control-plane",
      nodeType: providers[0].nodeTypes[1],
      count: 1,
      region: providers[0].regions[1]
    },
    nodePools: [
      {
        id: "pool-3",
        name: "default-pool",
        nodeType: providers[0].nodeTypes[3],
        count: 2,
        region: providers[0].regions[1]
      },
    ],
    status: stateEnum.FAILED,
    errorMessage: "Resource not available",
    created: "2023-10-05T11:30:00Z",
    deployments: [
      {
        id: "app-2",
        name: "JupyterHub Deployment",
        application: applications[2],
        status: stateEnum.RUNNING,
        config: {
          auth_type: "native",
          default_image: "jupyter/datascience-notebook:latest",
          resource_limits: "medium",
        },
        deployedAt: "2023-10-06T09:15:00Z",
      },
    ],
  },
];

export const volumes: Volume[] = [
  {
    id: "vol-1",
    name: "Airflow Logs",
    size: 10,
    provider: "hetzner",
    region: "fsn1",
    status: stateEnum.RUNNING,
    createdAt: "2025-01-15T08:30:00Z",
    description: "Storage for Airflow logs data",
    inUse: false,
  },
  {
    id: "vol-2",
    name: "Airflow DAGs",
    size: 5,
    provider: "hetzner",
    region: "nbg1",
    status: stateEnum.RUNNING,
    createdAt: "2025-01-17T12:15:00Z",
    description: "Storage for Airflow DAG files",
    inUse: true,
  },
  {
    id: "vol-3",
    name: "Grafana Data",
    size: 15,
    provider: "hetzner",
    region: "hel1",
    status: stateEnum.DEPLOYING,
    createdAt: "2025-02-20T09:45:00Z",
    description: "Storage for Grafana metrics data",
    inUse: false,
  },
];
