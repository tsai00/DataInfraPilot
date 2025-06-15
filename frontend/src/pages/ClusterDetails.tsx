import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import {
  Cloud,
  Database,
  Server,
  Settings,
  Trash,
  Plus,
  ExternalLink,
  Download,
  Cpu,
  DollarSign,
  Clock,
  MoreVertical,
  Flower,
  ArrowRight,
  ArrowUpCircle,
  Link2,
  ArrowsUpFromLine,
  CheckCircle,
  XCircle,
  Euro,
} from "lucide-react";
import { useClusterStore } from "@/store";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import DeployAppModal from "@/components/applications/DeployAppModal";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
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
import { useToast } from "@/hooks/use-toast";
import { Separator } from "@/components/ui/separator";
import { stateEnum } from "@/types/stateEnum";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
  ContextMenuSeparator,
} from "@/components/ui/context-menu";
import StatusComponent from "@/components/StatusComponent";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { calculateClusterCost } from "@/utils/costCalculations";

const ClusterDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { clusters, deleteCluster, downloadKubeconfig, fetchClusters, deleteDeployment: removeApplication } = useClusterStore();
  const { toast } = useToast();
  const cluster = clusters.find((c) => c.id === id);

  const [showDeployAppModal, setShowDeployAppModal] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [selectedAppForUpdate, setSelectedAppForUpdate] = useState<string | null>(null);

  useEffect(() => {
    fetchClusters();
  }, [fetchClusters]);

  if (!cluster) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Cluster Not Found</AlertTitle>
        <AlertDescription>
          The requested cluster does not exist. Please check the ID and try
          again.
        </AlertDescription>
      </Alert>
    );
  }

  const handleDeleteCluster = () => {
    deleteCluster(cluster.id);
    toast({
      title: "Cluster deletion started",
      description: `${cluster.name} is being deleted. This may take a few minutes.`,
    });
    navigate("/clusters");
  };

  const handleDownloadKubeconfig = async () => {
    try {
      setIsDownloading(true);
      await downloadKubeconfig(cluster.id);
      toast({
        title: "Kubeconfig downloaded",
        description: `Kubeconfig for ${cluster.name} has been downloaded successfully.`,
      });
    } catch (error) {
      toast({
        title: "Download failed",
        description: "Failed to download kubeconfig. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsDownloading(false);
    }
  };

  const handleUpgradeVersion = () => {
    toast({
      title: "Coming soon",
      description: "K3s version upgrade will be available soon.",
    });
  };

  const totalCost = calculateClusterCost(cluster);
  const totalNodes = cluster.nodePools.reduce(
    (total, pool) => {
      const nodeCount = pool.autoscaling?.enabled ? pool.autoscaling.maxNodes : pool.count;
      return total + nodeCount;
    }, 
    0
  ) + cluster.controlPlane.count;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">{cluster.name}</h1>
          <p className="text-muted-foreground">
            Manage your Kubernetes cluster
          </p>
        </div>
        <div className="space-x-2">
          {cluster.additionalComponents?.traefik_dashboard?.enabled ? (
            <Button variant="secondary" disabled={cluster.status !== stateEnum.RUNNING}>
              <a
                href={cluster.domainName ? `https://${cluster.domainName}/traefik/dashboard/` : `http://${cluster.access_ip}/traefik/dashboard/`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center"
              >
                <ExternalLink className="mr-2 h-4 w-4" /> Traefik Dashboard 
              </a>
            </Button>
          ): ''}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="secondary">
                <Settings className="mr-2 h-4 w-4" /> Settings
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuItem 
                onClick={handleDownloadKubeconfig}
                disabled={isDownloading || cluster.status !== stateEnum.RUNNING}
              >
                <Download className="mr-2 h-4 w-4" /> Download Kubeconfig
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={handleUpgradeVersion}
                disabled={cluster.status !== stateEnum.RUNNING}
              >
                <ArrowUpCircle className="mr-2 h-4 w-4" /> Upgrade K3s Version
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive">
                <Trash className="mr-2 h-4 w-4" /> Delete Cluster
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action cannot be undone. This will permanently delete{" "}
                  {cluster.name} and all of its data.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleDeleteCluster}>
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Overview</CardTitle>
            <CardDescription>Cluster details and status</CardDescription>
          </CardHeader>
          <CardContent className="p-6">
            <div className="space-y-4">
              <div className="flex justify-between">
                <span>Status:</span>
                <StatusComponent status={cluster.status} errorMessage={cluster.errorMessage}/>
              </div>
              <div className="flex justify-between">
                <span>Access IP:</span>
                <span>{cluster.access_ip}</span>
              </div>
              {cluster.domainName ? (
                <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium">Domain Name</span>
                </div>
                <span>{cluster.domainName}</span>
              </div>
              ) : ''}
              <div className="flex justify-between">
                <span>Provider:</span>
                <span>{cluster.provider.name}</span>
              </div>
              <div className="flex justify-between">
                <span>Version:</span>
                <span>{cluster.version}</span>
              </div>
              <div className="flex justify-between">
                <span>Created:</span>
                <span>{new Date(cluster.created).toLocaleDateString()}</span>
              </div>
              <Separator />
              <div className="space-y-3">
                <span className="font-medium text-sm">Additional Components:</span>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Traefik Dashboard:</span>
                    <div className="flex items-center gap-1">
                      {cluster.additionalComponents?.traefik_dashboard?.enabled ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-gray-400" />
                      )}
                      <span className="text-sm">
                        {cluster.additionalComponents?.traefik_dashboard?.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <Separator />
              <div className="flex justify-between font-medium">
                <span>Total Nodes:</span>
                <span>{totalNodes}</span>
              </div>
              <div className="flex justify-between font-medium">
                <span>Monthly Cost:</span>
                <span>{totalCost.monthly.toFixed(2)} €</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Control Plane</CardTitle>
            <CardDescription>Control plane configuration</CardDescription>
          </CardHeader>
          <CardContent className="p-6">
            <Card className="bg-secondary/30 border border-secondary">
              <CardContent className="p-4">
                <div className="flex justify-between items-center mb-2">
                  <div className="flex items-center">
                    <Cpu className="w-5 h-5 mr-2 text-primary" />
                    <span className="font-medium">{cluster.controlPlane.nodeType.name}</span>
                  </div>
                  <Badge variant="outline">{cluster.controlPlane.count} {cluster.controlPlane.count === 1 ? 'node' : 'nodes'}</Badge>
                </div>
                <div className="flex justify-between items-center mb-1 text-sm">
                  <span>Region:</span>
                  <span className="flex items-center">
                    {cluster.controlPlane.region.flag} {cluster.controlPlane.region.name}, {cluster.controlPlane.region.location}
                  </span>
                </div>
                <div className="flex justify-between items-center mb-1 text-sm">
                  <span>Resources:</span>
                  <span>{cluster.controlPlane.nodeType.cpu} vCPU • {cluster.controlPlane.nodeType.memory} GB RAM</span>
                </div>
                <Separator className="my-2" />
                <div className="flex justify-end text-sm">
                  <div className="flex items-center">
                    <Euro className="h-4 w-4 mr-1 text-muted-foreground" />
                    <span>{cluster.controlPlane.nodeType.hourlyCost.toFixed(4)} / hr ({(cluster.controlPlane.nodeType.hourlyCost * 24 * 30).toFixed(2)} / month)</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Node Pools</CardTitle>
            <CardDescription>Compute resources</CardDescription>
          </CardHeader>
          <CardContent className="p-6 overflow-y-auto max-h-[400px]">
            <div className="space-y-4">
              {cluster.nodePools.map((pool) => (
                <Card key={pool.id} className="bg-secondary/30 border border-secondary">
                  <CardContent className="p-4">
                    <div className="flex justify-between items-center mb-2">
                      <div className="flex items-center">
                        <Server className="w-5 h-5 mr-2 text-primary" />
                        <span className="font-medium">{pool.name} ({pool.nodeType.name})</span>
                      </div>
                        {pool.autoscaling?.enabled ? <Badge variant="outline">Auto ({pool.autoscaling.minNodes} - {pool.autoscaling.maxNodes})</Badge> : <Badge variant="outline">{pool.count} {pool.count === 1 ? 'node' : 'nodes'}</Badge> }
                    </div>
                    <div className="flex justify-between items-center mb-1 text-sm">
                      <span>Region:</span>
                      <span className="flex items-center">
                        {pool.region?.flag} {pool.region?.name}, {pool.region?.location}
                      </span>
                    </div>
                    <div className="flex justify-between items-center mb-1 text-sm">
                      <span>Resources:</span>
                      <span>{pool.nodeType.cpu} vCPU • {pool.nodeType.memory} GB RAM</span>
                    </div>
                    <Separator className="my-2" />
                    <div className="flex justify-end text-sm">
                      <div className="flex items-center">
                        <Euro className="h-4 w-4 mr-1 text-muted-foreground" />
                        {pool.autoscaling?.enabled ? (
                          <span>
                            {(pool.nodeType.hourlyCost * pool.autoscaling.minNodes).toFixed(4)}-{(pool.nodeType.hourlyCost * pool.autoscaling.maxNodes).toFixed(4)} / hr 
                            ({(pool.nodeType.hourlyCost * pool.autoscaling.minNodes * 24 * 30).toFixed(2)}-{(pool.nodeType.hourlyCost * pool.autoscaling.maxNodes * 24 * 30).toFixed(2)} / month)
                          </span>
                        ) : (
                          <span>
                            {((pool.nodeType.hourlyCost * pool.count).toFixed(4))} / hr ({(pool.nodeType.hourlyCost * pool.count * 24 * 30).toFixed(2)} / month)
                          </span>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="mb-6">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <CardTitle>Deployments</CardTitle>
            <CardDescription>
              Deployed applications and their status
            </CardDescription>
          </div>
          <Button
            variant="secondary"
            onClick={() => setShowDeployAppModal(true)}
            disabled={cluster.status !== stateEnum.RUNNING}
          >
            <Plus className="mr-2 h-4 w-4" /> New Deployment
          </Button>
        </CardHeader>
        <CardContent className="p-6">
          {cluster.deployments && cluster.deployments.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {cluster.deployments.map((deployment) => (
                deployment && deployment.application ? (
                  <ContextMenu key={deployment.id}>
                    <ContextMenuTrigger>
                      <Card 
                        key={deployment.id} 
                        className="relative group overflow-hidden hover:border-primary/50 transition-all duration-300 hover:shadow-lg"
                        onClick={() => navigate(`/clusters/${cluster.id}/deployments/${deployment.id}`)}
                      >
                        <div className="absolute top-2 right-2 z-10">
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-8 w-8"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedAppForUpdate(deployment.id);
                            }}
                          >
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </div>
                        <CardContent className="p-6">
                          <div className="flex flex-col items-center text-center gap-3">
                            <div className="relative">
                              <div className="p-3 rounded-xl">
                                <img
                                  src={deployment.application.logo}
                                  alt={deployment.application.name}
                                  className="w-16 h-16 object-contain bg-white rounded-lg p-2"
                                />
                              </div>
                            </div>
                            <div className="space-y-2">
                              <h3 className="font-semibold tracking-tight">
                                {deployment.name || deployment.application.name}
                              </h3>
                              <div className="flex items-center justify-center mb-2">
                                <StatusComponent status={deployment.status} errorMessage={deployment.errorMessage}/>
                              </div>
                              <Button 
                                variant="secondary" 
                                size="sm" 
                                className="w-full mt-2 text-xs gap-1"
                                asChild
                              >
                                <Link to={`/deployments/${cluster.id}/${deployment.id}`}>
                                  Details <ArrowRight className="h-3 w-3" />
                                </Link>
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem
                        onClick={() => navigate(`/clusters/${cluster.id}/deployments/${deployment.id}`)}
                      >
                        <ArrowRight className="mr-2 h-4 w-4" /> View Details
                      </ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem
                        onClick={() => setSelectedAppForUpdate(deployment.id)}
                      >
                        <Settings className="mr-2 h-4 w-4" /> Update Config
                      </ContextMenuItem>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <ContextMenuItem
                            className="text-red-600"
                            onSelect={(e) => e.preventDefault()}
                          >
                            <Trash className="mr-2 h-4 w-4" /> Remove Deployment
                          </ContextMenuItem>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                            <AlertDialogDescription>
                              This will permanently delete {deployment.name} from this cluster.
                              This action cannot be undone.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction 
                              onClick={() => cluster && removeApplication(cluster.id, deployment.id)}
                              className="bg-red-600 hover:bg-red-700"
                            >
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </ContextMenuContent>
                  </ContextMenu>
                ) : null
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Database className="mx-auto h-12 w-12 opacity-20 mb-2" />
              <p>No applications deployed yet.</p>
              <p className="text-sm">Deploy an application to get started.</p>
            </div>
          )}
        </CardContent>
      </Card>

      <DeployAppModal
        open={showDeployAppModal}
        onClose={() => setShowDeployAppModal(false)}
        clusterId={cluster.id}
      />
    </div>
  );
};

export default ClusterDetails;
