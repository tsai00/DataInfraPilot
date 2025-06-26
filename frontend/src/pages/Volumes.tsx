
import React, { useState, useEffect } from "react";
import { useClusterStore } from "@/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Volume } from "@/types";
import { stateEnum } from "@/types/stateEnum";
import { HardDrive, Plus, Trash, Server, Database, Calendar, Coins } from "lucide-react";
import { toast } from "sonner";

const Volumes: React.FC = () => {
  const { volumes, providers, createVolume, deleteVolume } = useClusterStore();

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newVolumeName, setNewVolumeName] = useState("");
  const [newVolumeSize, setNewVolumeSize] = useState(10); // Default to 10GB
  const [newVolumeProvider, setNewVolumeProvider] = useState("");
  const [newVolumeRegion, setNewVolumeRegion] = useState("");
  const [volumeToDelete, setVolumeToDelete] = useState<Volume | null>(null);
  const [isConfirmDeleteDialogOpen, setIsConfirmDeleteDialogOpen] = useState(false);
    
  // Get regions for selected provider
  const selectedProvider = providers.find(p => p.id === newVolumeProvider);
  const availableRegions = selectedProvider ? selectedProvider.regions : [];

  const handleCreateVolume = () => {
    if (!newVolumeName || !newVolumeProvider || !newVolumeRegion) {
      toast.error("Missing information", {
        description: "Please fill in all required fields."
      });
      return;
    }

    createVolume(
      newVolumeName,
      newVolumeSize,
      newVolumeProvider,
      newVolumeRegion
    );

    // Reset form and close dialog
    setNewVolumeName("");
    setNewVolumeSize(10);
    setNewVolumeProvider("");
    setNewVolumeRegion("");
    setIsCreateDialogOpen(false);
  };

  const handleDeleteClick = (volume: Volume) => {
    if (volume.inUse) {
      toast.error("Cannot delete volume", {
        description: "This volume is currently in use by a deployment."
      });
      return;
    }
    
    setVolumeToDelete(volume);
    setIsConfirmDeleteDialogOpen(true);
  };

  const handleConfirmDelete = () => {
    if (volumeToDelete) {
      deleteVolume(volumeToDelete.id);
      setVolumeToDelete(null);
      setIsConfirmDeleteDialogOpen(false);
    }
  };

  const getStatusBadgeColor = (status: stateEnum) => {
    switch (status) {
      case stateEnum.RUNNING:
        return "bg-green-500";
      case stateEnum.CREATING:
        return "bg-blue-500";
      case stateEnum.DELETING:
        return "bg-red-500";
      case stateEnum.FAILED:
        return "bg-red-600";
      default:
        return "bg-gray-500";
    }
  };

  return (
    <div className="mx-auto py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Data Volumes</h1>
          <p className="text-muted-foreground mt-1">
            Manage persistent storage volumes for your applications
          </p>
        </div>
        <Button onClick={() => setIsCreateDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Volume
        </Button>
      </div>

      <Card className="mb-8">
        <CardHeader className="pb-3">
          <CardTitle>Volumes</CardTitle>
          <CardDescription>
            Persistent storage volumes for your application data
          </CardDescription>
        </CardHeader>
        <CardContent>
          {volumes.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Region</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Costs</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {volumes.map((volume) => {
                  const provider = providers.find(p => p.id === volume.provider);
                  const region = provider?.regions.find(r => r.id === volume.region);
                  
                  return (
                    <TableRow key={volume.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center">
                          <HardDrive className="h-4 w-4 mr-2" />
                          {volume.name}
                        </div>
                      </TableCell>
                      <TableCell>{volume.size} GB</TableCell>
                      <TableCell>
                        <div className="flex items-center">
                          {provider?.name || volume.provider}
                        </div>
                      </TableCell>
                      <TableCell>
                        {region ? (
                          <div className="flex items-center">
                            <span className="text-lg mr-2">{region.flag}</span>
                            {region.name}
                          </div>
                        ) : (
                          volume.region
                        )}
                      </TableCell>
                      <TableCell>
                        {volume.description ? (
                          <div className="flex items-center">
                            <Database className="h-4 w-4 mr-2" />
                            {volume.description}
                          </div>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={`${getStatusBadgeColor(volume.status)} text-white`}
                        >
                          {volume.inUse ? "In Use" : volume.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{new Date(volume.createdAt).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <div className="flex items-center">
                          $ {(0.0484 * volume.size).toFixed(2)}/month
                        </div>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteClick(volume)}
                          disabled={volume.inUse || volume.status === stateEnum.DELETING}
                        >
                          <Trash className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Database className="h-12 w-12 mb-4 text-muted-foreground" />
              <h3 className="text-lg font-medium mb-1">No volumes found</h3>
              <p className="text-muted-foreground mb-4">
                You haven't created any volumes yet
              </p>
              <Button onClick={() => setIsCreateDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Volume
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Volume Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Volume</DialogTitle>
            <DialogDescription>
              Set up a new persistent storage volume for your applications
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="volumeName">Volume Name</Label>
              <Input
                id="volumeName"
                value={newVolumeName}
                onChange={(e) => setNewVolumeName(e.target.value)}
                placeholder="e.g., airflow-logs-prod"
              />
              <p className="text-xs text-muted-foreground">
                A unique name to identify your volume
              </p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="volumeSize">
                Size (GB): {newVolumeSize} GB
              </Label>
              <Slider
                id="volumeSize"
                value={[newVolumeSize]}
                min={10}
                max={1000}
                step={1}
                onValueChange={(values) => setNewVolumeSize(values[0])}
              />
              <p className="text-xs text-muted-foreground">
                Choose a volume size between 10GB and 1000GB
              </p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="volumeProvider">Cloud Provider</Label>
              <Select
                value={newVolumeProvider}
                onValueChange={setNewVolumeProvider}
              >
                <SelectTrigger id="volumeProvider">
                  <SelectValue placeholder="Select provider" />
                </SelectTrigger>
                <SelectContent>
                  {providers.map((provider) => (
                    <SelectItem key={provider.id} value={provider.id}>
                      <div className="flex items-center">
                        <img
                          src={provider.logo}
                          alt={provider.name}
                          className="h-4 w-4 mr-2"
                        />
                        {provider.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="volumeRegion">Region</Label>
              <Select
                value={newVolumeRegion}
                onValueChange={setNewVolumeRegion}
                disabled={availableRegions.length === 0}
              >
                <SelectTrigger id="volumeRegion">
                  <SelectValue placeholder="Select region" />
                </SelectTrigger>
                <SelectContent>
                  {availableRegions.map((region) => (
                    <SelectItem key={region.id} value={region.id}>
                      <div className="flex items-center">
                        <span className="text-lg mr-2">{region.flag}</span>
                        <span>
                          {region.name}, {region.location}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <Card 
            className="bg-gradient-to-br from-soft-purple/40 to-soft-blue/40 border-2 border-primary/20 shadow-md"
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center">
                <Coins className="mr-2 h-5 w-5 text-primary" />
                Cost Summary
              </CardTitle>
              <CardDescription>Estimated volume costs</CardDescription>
            </CardHeader>
            <CardContent className="pb-3 space-y-2">
              <div className="flex justify-between items-center bg-soft-purple/20 p-2 rounded-lg mt-2">
                <span className="text-sm font-semibold flex items-center">
                  <Calendar className="h-5 w-5 mr-2 text-primary" />
                  Monthly Cost (billed hourly)
                </span>
                <span className="text-lg font-bold text-primary">
                  {(newVolumeSize * 0.044).toFixed(2)} €/month
                </span>
              </div>
            </CardContent>
          </Card>
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setIsCreateDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleCreateVolume}
              disabled={!newVolumeName || !newVolumeProvider || !newVolumeRegion}
            >
              Create Volume
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Delete Confirmation Dialog */}
      <Dialog open={isConfirmDeleteDialogOpen} onOpenChange={setIsConfirmDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Deletion</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the volume &quot;{volumeToDelete?.name}&quot;? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setIsConfirmDeleteDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleConfirmDelete}
            >
              Delete Volume
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Volumes;
