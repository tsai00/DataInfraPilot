
import React, {  } from 'react';
import { Application } from "@/types";
import VolumeSelectionField from './VolumeSelectionField';

interface StorageConfigStepProps {
  selectedApp: Application;
  providerId: string;
  updateVolumeSelection: (volumeType?: string, size?: number, name?: string) => void;
}

const StorageConfigStep: React.FC<StorageConfigStepProps> = ({
  selectedApp,
  providerId,
  updateVolumeSelection
}) => {

  return (
    <div className="space-y-6 py-4">
      <div className="space-y-4">
        <h3 className="font-medium">Storage Configuration</h3>
        <div className="space-y-6 border rounded-lg p-4 bg-secondary/10">
          {selectedApp?.volumeRequirements ? (
            <div className="space-y-6">
              {selectedApp?.volumeRequirements?.map((volReq) => (
                <VolumeSelectionField
                  key={volReq.id}
                  volumeRequirement={volReq}
                  providerId={providerId}
                  onVolumeSelected={(name, size) => 
                    updateVolumeSelection("existing", size, name)}
                />
              ))}
            </div>
          ) : (
            <span className="text-muted-foreground">{selectedApp.name} does not have any requirements for storage</span>
          )}
        </div>
      </div>
    </div>
  );
};


export default StorageConfigStep;
