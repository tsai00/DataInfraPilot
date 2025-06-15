import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import {
  Cloud,
  Database,
  Plus,
  Server,
  Search,
  Calendar,
  DollarSign,
  HardDrive,
  MoreVertical,
  Link2,
  Euro,
  Eye,
  Settings,
  Trash2,
  Power,
  PowerOff,
  Trash,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useClusterStore } from "@/store";
import CreateClusterModal from "@/components/clusters/CreateClusterModal";
import { useToast } from "@/hooks/use-toast";
import StatusComponent from "@/components/StatusComponent";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

const Clusters: React.FC = () => {
  const { clusters, providers, fetchClusters, deleteCluster } = useClusterStore();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState("");
  const [providerFilter, setProviderFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [showCreateCluster, setShowCreateCluster] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [clusterToDelete, setClusterToDelete] = useState<string | null>(null);

  useEffect(() => {
    const loadClusters = async () => {
      try {
        setIsLoading(true);
        await fetchClusters();
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to load clusters. Please try again.",
          variant: "destructive",
        });
      } finally {
        setIsLoading(false);
      }
    };
    
    loadClusters();
  }, [fetchClusters, toast]);

  const filteredClusters = clusters.filter((cluster) => {
    const matchesSearch = cluster.name
      .toLowerCase()
      .includes(searchTerm.toLowerCase());
    const matchesProvider =
      providerFilter === "all" || cluster.provider.id === providerFilter;
    const matchesStatus =
      statusFilter === "all" || cluster.status === statusFilter;
    return matchesSearch && matchesProvider && matchesStatus;
  });

  const handleClusterAction = async (action: string, clusterId: string) => {
    console.log(`${action} action triggered for cluster:`, clusterId);
    
    switch (action) {
      case "view":
        navigate(`/clusters/${clusterId}`);
        break;
      case "manage":
        toast({
          title: "Manage Cluster",
          description: "Cluster management functionality coming soon.",
        });
        break;
      case "start":
        toast({
          title: "Starting Cluster",
          description: "Cluster start functionality coming soon.",
        });
        break;
      case "stop":
        toast({
          title: "Stopping Cluster",
          description: "Cluster stop functionality coming soon.",
        });
        break;
      case "delete":
        const cluster = clusters.find(c => c.id === clusterId);
        if (cluster) {
          try {
            await deleteCluster(clusterId);
            toast({
              title: "Cluster Deletion Started",
              description: `${cluster.name} is being deleted. This may take a few minutes.`,
            });
          } catch (error) {
            toast({
              title: "Delete Failed",
              description: "Failed to delete the cluster. Please try again.",
              variant: "destructive",
            });
          }
        }
        break;
      default:
        break;
    }
  };

  const handleDeleteClick = (clusterId: string) => {
    setClusterToDelete(clusterId);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (clusterToDelete) {
      handleClusterAction("delete", clusterToDelete);
    }
    setDeleteDialogOpen(false);
    setClusterToDelete(null);
  };

  return (
    <>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Clusters</h1>
          <p className="text-muted-foreground">
            Manage your Kubernetes clusters
          </p>
        </div>
        <Button onClick={() => setShowCreateCluster(true)}>
          <Plus className="mr-2 h-4 w-4" /> Create Cluster
        </Button>
      </div>

      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="relative w-full md:w-1/3">
          <Search className="absolute top-2.5 left-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search clusters..."
            className="pl-10"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-4 w-full md:w-2/3">
          <Select
            value={providerFilter}
            onValueChange={setProviderFilter}
          >
            <SelectTrigger>
              <SelectValue placeholder="Filter by provider" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Providers</SelectItem>
              {providers.map((provider) => (
                <SelectItem key={provider.id} value={provider.id}>
                  {provider.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={statusFilter}
            onValueChange={setStatusFilter}
          >
            <SelectTrigger>
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="creating">Creating</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="updating">Updating</SelectItem>
              <SelectItem value="error">Error</SelectItem>
              <SelectItem value="deleting">Deleting</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-medium">Your clusters</h2>
        <Button variant="outline" size="sm" onClick={() => setShowCreateCluster(true)}>
          <Plus className="h-4 w-4 mr-1" /> Add Cluster
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-k8s-blue"></div>
        </div>
      ) : filteredClusters.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredClusters.map((cluster) => (
            <ContextMenu key={cluster.id}>
              <ContextMenuTrigger asChild>
                <div className="h-full">
                  <Link to={`/clusters/${cluster.id}`}>
                    <Card className="h-full hover:shadow-md transition-all cursor-pointer">
                      <CardHeader className="pb-2">
                        <div className="flex justify-between items-start">
                          <div>
                            <CardTitle className="text-xl">{cluster.name} - {cluster.domainName ? cluster.domainName : cluster.access_ip && cluster.access_ip}</CardTitle>
                            <CardDescription>
                              {cluster.provider.name} · {cluster.controlPlane.region.name},{" "}
                              {cluster.controlPlane.region.location} {cluster.controlPlane.region.flag}
                            </CardDescription>
                          </div>
                          <StatusComponent status={cluster.status} errorMessage={cluster.errorMessage}/>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 gap-2 mb-4">
                          <div className="flex flex-col">
                            <span className="text-xs text-muted-foreground mb-1">
                              Node Count
                            </span>
                            <div className="flex items-center">
                              <Server className="h-4 w-4 mr-2 text-muted-foreground" />
                              <span>
                                {cluster.nodePools.reduce(
                                  (total, pool) => total + pool.count,
                                  0
                                ) + cluster.controlPlane.count}
                              </span>
                            </div>
                          </div>
                          <div className="flex flex-col">
                            <span className="text-xs text-muted-foreground mb-1">
                              Application Deployments
                            </span>
                            <div className="flex items-center">
                              <Database className="h-4 w-4 mr-2 text-muted-foreground" />
                              <span>{cluster.deployments.length}</span>
                            </div>
                          </div>
                          <div className="flex flex-col">
                            <span className="text-xs text-muted-foreground mb-1">
                              Created
                            </span>
                            <div className="flex items-center">
                              <Calendar className="h-4 w-4 mr-2 text-muted-foreground" />
                              <span>
                                {new Date(cluster.created).toLocaleDateString()}
                              </span>
                            </div>
                          </div>
                          <div className="flex flex-col">
                            <span className="text-xs text-muted-foreground mb-1">
                              K8s Version
                            </span>
                            <div className="flex items-center">
                              <HardDrive className="h-4 w-4 mr-2 text-muted-foreground" />
                              <span>{cluster.version}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center justify-between pt-2 border-t">
                          <div className="text-sm">Monthly cost:</div>
                          <div className="flex items-center text-right">
                            <Euro className="h-4 w-4 mr-1 text-muted-foreground" />
                            <span className="font-medium">
                              {(
                                (cluster.nodePools.reduce(
                                  (total, pool) =>
                                    total + pool.nodeType.hourlyCost * pool.count,
                                  0
                                ) + 
                                (cluster.controlPlane.nodeType.hourlyCost * 
                                 cluster.controlPlane.count)) * 24 * 30
                              ).toFixed(2)}
                            </span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                </div>
              </ContextMenuTrigger>
              <ContextMenuContent className="w-48">
                <ContextMenuItem onClick={() => handleClusterAction("view", cluster.id)}>
                  <Eye className="mr-2 h-4 w-4" />
                  View Details
                </ContextMenuItem>
                <ContextMenuSeparator />
                <ContextMenuItem
                  className="text-red-600"
                  onClick={() => handleDeleteClick(cluster.id)}
                >
                  <Trash className="mr-2 h-4 w-4" /> Remove Cluster
                </ContextMenuItem>
              </ContextMenuContent>
            </ContextMenu>
          ))}
          <button 
            onClick={() => setShowCreateCluster(true)}
            className="h-full border-2 border-dashed border-muted-foreground/20 rounded-lg p-8 flex flex-col items-center justify-center hover:border-primary/30 hover:bg-accent/50 transition-all group"
          >
            <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-3 group-hover:bg-primary/20 transition-transform">
              <Plus className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-lg font-medium mb-1">Add cluster</h3>
          </button>
        </div>
      ) : (
        searchTerm || providerFilter !== "all" || statusFilter !== "all" ? (
          <div className="flex flex-col items-center justify-center p-12 border rounded-lg bg-card">
            <Cloud className="h-16 w-16 text-muted-foreground/30 mb-4" />
            <h3 className="text-xl font-medium mb-2">No clusters found</h3>
            <p className="text-center text-muted-foreground mb-6">
              No clusters match your search criteria. Try adjusting your filters.
            </p>
            <Button onClick={() => setShowCreateCluster(true)}>
              <Plus className="mr-2 h-4 w-4" /> Create Cluster
            </Button>
          </div>
        ) : (
          <button 
            onClick={() => setShowCreateCluster(true)}
            className="w-full border-2 border-dashed border-muted-foreground/20 rounded-lg p-12 flex flex-col items-center justify-center hover:border-primary/30 hover:bg-accent/50 transition-all group"
          >
            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
              <Plus className="h-8 w-8 text-primary" />
            </div>
            <h3 className="text-xl font-medium mb-2">Create your first cluster</h3>
          </button>
        )
      )}

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete cluster {clusterToDelete ? clusters.find(c => c.id === clusterToDelete)?.name : ''}. 
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteConfirm}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <CreateClusterModal
        open={showCreateCluster}
        onClose={() => setShowCreateCluster(false)}
      />
    </>
  );
};

export default Clusters;
