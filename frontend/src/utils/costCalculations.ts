
import { Cluster, NodePool, Volume, Provider } from "@/types";

export type CostPeriod = 'hourly' | 'monthly';

export interface CostCalculationResult {
  hourly: number;
  monthly: number;
}

/**
 * Calculate the cost for node pools
 */
export function calculateNodePoolsCost(nodePools: NodePool[]): CostCalculationResult {
  const hourlyNodePoolsCost = nodePools.reduce(
    (total, pool) => {
      const nodeCount = pool.autoscaling?.enabled 
        ? pool.autoscaling.maxNodes 
        : pool.count;
      
      return total + pool.nodeType.hourlyCost * nodeCount;
    },
    0
  );
  
  return {
    hourly: parseFloat(hourlyNodePoolsCost.toFixed(2)),
    monthly: parseFloat((hourlyNodePoolsCost * 24 * 30).toFixed(2))
  };
}

/**
 * Calculate the cost for a single cluster including control plane and node pools
 */
export function calculateClusterCost(cluster: Cluster): CostCalculationResult {
  // Calculate node pools cost
  const nodePoolsCost = calculateNodePoolsCost(cluster.nodePools);
  
  // Add control plane cost
  const controlPlaneCost = cluster.controlPlane.nodeType.hourlyCost * 
                          cluster.controlPlane.count;
  
  const totalHourly = nodePoolsCost.hourly + controlPlaneCost;
  
  return {
    hourly: parseFloat(totalHourly.toFixed(2)),
    monthly: parseFloat((totalHourly * 24 * 30).toFixed(2))
  };
}

/**
 * Calculate the estimated cost for cluster creation form
 */
export function calculateClusterEstimatedCost(
  controlPlane: NodePool,
  nodePools: NodePool[]
): CostCalculationResult {
  // Calculate control plane cost
  const controlPlaneCost = controlPlane.nodeType.hourlyCost * controlPlane.count;
  
  // Calculate node pools cost
  const nodePoolsCost = calculateNodePoolsCost(nodePools);
  
  const totalHourly = controlPlaneCost + nodePoolsCost.hourly;
  
  return {
    hourly: parseFloat(totalHourly.toFixed(2)),
    monthly: parseFloat((totalHourly * 24 * 30).toFixed(2))
  };
}

/**
 * Calculate minimum and maximum costs for node pools with autoscaling
 */
export function calculateNodePoolCostRange(nodePools: NodePool[]): {
  min: CostCalculationResult;
  max: CostCalculationResult;
} {
  const minHourly = nodePools.reduce((total, pool) => {
    const nodeCount = pool.autoscaling?.enabled 
      ? pool.autoscaling.minNodes 
      : pool.count;
    return total + pool.nodeType.hourlyCost * nodeCount;
  }, 0);
  
  const maxHourly = nodePools.reduce((total, pool) => {
    const nodeCount = pool.autoscaling?.enabled 
      ? pool.autoscaling.maxNodes 
      : pool.count;
    return total + pool.nodeType.hourlyCost * nodeCount;
  }, 0);
  
  return {
    min: {
      hourly: parseFloat(minHourly.toFixed(2)),
      monthly: parseFloat((minHourly * 24 * 30).toFixed(2))
    },
    max: {
      hourly: parseFloat(maxHourly.toFixed(2)),
      monthly: parseFloat((maxHourly * 24 * 30).toFixed(2))
    }
  };
}

/**
 * Calculate minimum and maximum costs for cluster with autoscaling
 */
export function calculateClusterCostRange(
  controlPlane: NodePool,
  nodePools: NodePool[]
): {
  min: CostCalculationResult;
  max: CostCalculationResult;
} {
  const controlPlaneCost = controlPlane.nodeType.hourlyCost * controlPlane.count;
  const nodePoolCostRange = calculateNodePoolCostRange(nodePools);
  
  return {
    min: {
      hourly: parseFloat((controlPlaneCost + nodePoolCostRange.min.hourly).toFixed(2)),
      monthly: parseFloat(((controlPlaneCost + nodePoolCostRange.min.hourly) * 24 * 30).toFixed(2))
    },
    max: {
      hourly: parseFloat((controlPlaneCost + nodePoolCostRange.max.hourly).toFixed(2)),
      monthly: parseFloat(((controlPlaneCost + nodePoolCostRange.max.hourly) * 24 * 30).toFixed(2))
    }
  };
}

/**
 * Calculate the cost for all clusters
 */
export function calculateAllClustersCost(clusters: Cluster[]): CostCalculationResult {
  const totalHourly = clusters.reduce((total, cluster) => {
    const clusterCost = calculateClusterCost(cluster);
    return total + clusterCost.hourly;
  }, 0);
  
  return {
    hourly: parseFloat(totalHourly.toFixed(2)),
    monthly: parseFloat((totalHourly * 24 * 30).toFixed(2))
  };
}

/**
 * Calculate the cost for volumes
 */
export function calculateVolumesCost(volumes: Volume[], providers: Provider[]): CostCalculationResult {
  const totalHourly = volumes?.reduce((total, volume) => {
    const provider = providers.find(p => p.id === volume.provider);
    if (provider && volume.status === 'running') {
      return total + (provider.volumeCostGbPerHour * volume.size);
    }
    return total;
  }, 0) || 0;
  
  return {
    hourly: parseFloat(totalHourly.toFixed(2)),
    monthly: parseFloat((totalHourly * 24 * 30).toFixed(2))
  };
}

/**
 * Calculate total infrastructure cost (clusters + volumes)
 */
export function calculateTotalInfrastructureCost(
  clusters: Cluster[], 
  volumes: Volume[], 
  providers: Provider[]
): CostCalculationResult {
  const clustersCost = calculateAllClustersCost(clusters);
  const volumesCost = calculateVolumesCost(volumes, providers);
  
  const totalHourly = clustersCost.hourly + volumesCost.hourly;
  
  return {
    hourly: parseFloat(totalHourly.toFixed(2)),
    monthly: parseFloat((totalHourly * 24 * 30).toFixed(2))
  };
}

/**
 * Get cost value based on period
 */
export function getCostForPeriod(cost: CostCalculationResult, period: CostPeriod): number {
  return cost[period];
}
