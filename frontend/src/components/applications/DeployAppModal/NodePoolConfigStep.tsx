
import React from 'react';
import { NodePool } from "@/types";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface NodePoolConfigStepProps {
  selectedNodePool: string;
  workerNodePools: NodePool[];
  setSelectedNodePool: (value: string) => void;
}

const NodePoolConfigStep: React.FC<NodePoolConfigStepProps> = ({
  selectedNodePool,
  workerNodePools,
  setSelectedNodePool
}) => {

  return (
    <div className="space-y-6 py-4">
      <div className="space-y-4">
        <h3 className="font-medium">Select Worker Node Pool</h3>
        <span className="text-muted-foreground">Select which node pool to deploy the application to</span>
          <Select
            value={selectedNodePool}
            defaultValue="noselection"
            onValueChange={setSelectedNodePool}
          >
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
                <SelectItem key="noselection" value="noselection">
                  No specific pool assignment
                </SelectItem>
              {workerNodePools.map((pool) => {
                const displayNodeCount = pool.autoscaling?.enabled 
                  ? `${pool.autoscaling.minNodes}-${pool.autoscaling.maxNodes}`
                  : pool.count;
                  
                return (
                  <SelectItem key={pool.name} value={pool.name}>
                    {pool.name} ({displayNodeCount} nodes - {pool.nodeType.name})
                    {pool.autoscaling?.enabled && ` (Autoscaling)`}
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
      </div>
    </div>
  );
};

export default NodePoolConfigStep;
