
import React, { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";
import { useClusterStore } from "@/store";
import { VolumeRequirement } from "@/types";

interface VolumeSelectionFieldProps {
  providerId: string;
  volumeRequirement: VolumeRequirement;
  onVolumeSelected: (name?: string, size?: number) => void;
}

export function VolumeSelectionField({ 
  providerId, 
  volumeRequirement,
  onVolumeSelected 
}: VolumeSelectionFieldProps) {
  const { getAvailableVolumesForProvider } = useClusterStore();
  
  const [volumeType, setVolumeType] = useState<"new" | "existing">("new");
  const [selectedVolumeId, setSelectedVolumeId] = useState<string>("");
  const [volumeSize, setVolumeSize] = useState<number>(volumeRequirement.defaultSize);
  const [volumeName, setVolumeName] = useState<string>(`${volumeRequirement.name}`);
  
  const availableVolumes = getAvailableVolumesForProvider(providerId);
  
  useEffect(() => {
    if (availableVolumes.length > 0) {
      setSelectedVolumeId(availableVolumes[0].id);
    }
  }, [availableVolumes]);
  
  useEffect(() => {
    if (volumeType === "existing" && selectedVolumeId) {
      onVolumeSelected(volumeRequirement.name, volumeRequirement.defaultSize);
    } else {
      onVolumeSelected(volumeRequirement.name, volumeRequirement.defaultSize);
    }
  }, [volumeType, selectedVolumeId, volumeSize, volumeRequirement.id, onVolumeSelected, volumeRequirement.name, volumeRequirement.defaultSize]);
  
  return (
    <div className="space-y-4 mb-6">
      <div>
        <h4 className="text-sm font-medium mb-1">{volumeRequirement.name} Storage</h4>
        <p className="text-xs text-muted-foreground mb-3">
          {volumeRequirement.description}
        </p>
        
        <RadioGroup 
          value={volumeType} 
          onValueChange={(value: "new" | "existing") => setVolumeType(value)}
          className="flex flex-col space-y-3"
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="new" id={`new-${volumeRequirement.id}`} />
            <Label htmlFor={`new-${volumeRequirement.id}`}>Create new volume</Label>
          </div>
          
          <div className="flex items-center space-x-2">
            <RadioGroupItem 
              value="existing" 
              id={`existing-${volumeRequirement.id}`}
              disabled={availableVolumes.length === 0} 
            />
            <Label 
              htmlFor={`existing-${volumeRequirement.id}`}
              className={availableVolumes.length === 0 ? "text-muted-foreground" : ""}
            >
              Use existing volume
              {availableVolumes.length === 0 && " (none available)"}
            </Label>
          </div>
        </RadioGroup>
      </div>
      
      {volumeType === "new" ? (
        <div className="pl-6 space-y-4">
          <div className="space-y-2">
            <Label htmlFor={`name-${volumeRequirement.id}`}>Volume Name</Label>
            <Input
              id={`name-${volumeRequirement.id}`}
              value={volumeName}
              onChange={(e) => setVolumeName(e.target.value)}
              placeholder="Enter a name for your volume"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor={`size-${volumeRequirement.id}`}>
              Volume Size: {volumeSize} GB
            </Label>
            <Slider
              id={`size-${volumeRequirement.id}`}
              value={[volumeSize]}
              min={10}
              max={1000}
              step={1}
              onValueChange={(values) => setVolumeSize(values[0])}
            />
            <p className="text-xs text-muted-foreground">
              Choose a volume size between 10GB and 1000GB
            </p>
          </div>
        </div>
      ) : (
        <div className="pl-6 space-y-2">
          <Label htmlFor={`volume-${volumeRequirement.id}`} className="mb-1 block">
            Select Volume
          </Label>
          <Select 
            value={selectedVolumeId} 
            onValueChange={setSelectedVolumeId}
            disabled={availableVolumes.length === 0}
          >
            <SelectTrigger id={`volume-${volumeRequirement.id}`}>
              <SelectValue placeholder="Select a volume" />
            </SelectTrigger>
            <SelectContent>
              {availableVolumes.map((volume) => (
                <SelectItem key={volume.id} value={volume.id}>
                  {volume.name} ({volume.size} GB)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  );
}

export default VolumeSelectionField;
