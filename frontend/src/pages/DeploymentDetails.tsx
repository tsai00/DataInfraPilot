import React, { useMemo, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useClusterStore } from "@/store";
import { 
  ArrowLeft, 
  ExternalLink, 
  Server, 
  Calendar,
  Settings, 
  AlertTriangle,
  Trash,
  Key
} from "lucide-react";
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle,
  CardFooter
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from "@/components/ui/alert-dialog";
import { AccessEndpointType, Deployment } from "@/types";
import { stateEnum } from "@/types/stateEnum";
import UpdateConfigDialog from "@/components/applications/UpdateConfigDialog";
import StatusComponent from "@/components/StatusComponent";
import AppHealthCheck from "@/components/applications/AppHealthCheck";
import CredentialsModal from "@/components/applications/CredentialsModal";

const DeploymentDetails: React.FC = () => {
  const { clusterId, appId } = useParams<{ clusterId: string; appId: string }>();
  const navigate = useNavigate();
  const { clusters, deleteDeployment: removeApplication } = useClusterStore();
  const [showUpdateConfigDialog, setShowUpdateConfigDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showCredentialsModal, setShowCredentialsModal] = useState(false);

  const { currentDeployment, cluster, appEndpoints, primaryEndpoint, configDisplayData } = useMemo(() => {
    const foundCluster = clusters.find((c) => c.id === clusterId);
    const foundApp = foundCluster?.deployments.find((a) => a.id === appId);

    let builtEndpoints: Array<{
      id: string;
      name: string;
      description: string;
      path: string;
      icon: string;
    }> = [];
    let primaryEndpt = null;

    // Only build endpoints if we have both a deployment and cluster
    if (foundApp && foundCluster) {
      // Function to construct access URLs based on endpoint configuration
      if (foundApp.accessEndpoints && foundApp.accessEndpoints.length > 0) {
        // Filter endpoints based on deployment configuration
        const filteredAccessEndpoints = foundApp.accessEndpoints.filter(config => {
          // For Airflow, hide Flower UI if not using CeleryExecutor OR if Flower is disabled
          if (config.name === 'flower-ui' && foundApp.application.short_name === 'airflow') {
            const isCeleryExecutor = foundApp.config.executor === 'CeleryExecutor';
            const isFlowerEnabled = foundApp.config.flower_enabled === true;
            return isCeleryExecutor && isFlowerEnabled;
          }
          return true;
        });

        builtEndpoints = filteredAccessEndpoints.map(config => {
          const endpoint = {
            id: config.name,
            name: config.name.charAt(0).toUpperCase() + config.name.slice(1).replace(/-/g, ' ').replace(' ui', ' UI'),
            description: `${foundApp.application.name} interface`,
            path: config.value,
            icon: "ExternalLink"
          };

          let fullUrl;
          switch (config.access_type) {
            case AccessEndpointType.SUBDOMAIN:
              // Format: https://subdomain.domain.com/
              fullUrl = `https://${config.value}`;
              break;
            case AccessEndpointType.DOMAIN_PATH:
              // Format: https://domain.com/path
              fullUrl = `https://${config.value}`;
              break;
            case AccessEndpointType.CLUSTER_IP_PATH:
            default:
              // Format: http://ip/path
              fullUrl = `http://${foundCluster.access_ip}${config.value}`;
              break;
          }

          return {
            ...endpoint,
            path: fullUrl
          };
        });
      }

      // Set primary endpoint for health check (usually the main UI endpoint)
      primaryEndpt = builtEndpoints?.length > 0 ? builtEndpoints[0].path : null;
    }

    // Build configuration display data with names instead of IDs
    let configDisplay: Array<{ key: string; name: string; value: any }> = [];
    if (foundApp && foundApp.config) {
      // Special field name mappings for fields that don't have configOptions
      const specialFieldNames: Record<string, string> = {
        deployment_name: "Deployment Name",
        use_custom_image: "Use Custom Image",
        custom_image: "Custom Image",
        private_registry_url: "Private Registry URL",
        private_registry_username: "Private Registry Username",
        private_registry_password: "Private Registry Password",
      };

      configDisplay = Object.entries(foundApp.config).map(([configId, value]) => {
        // First check if it's a special field
        if (specialFieldNames[configId]) {
          return {
            key: configId,
            name: specialFieldNames[configId],
            value: value
          };
        }

        // Then check configOptions
        const configOption = foundApp.application.configOptions?.find(option => option.id === configId);
        return {
          key: configId,
          name: configOption ? configOption.name : configId,
          value: value
        };
      });
    }

    return {
      currentDeployment: foundApp,
      cluster: foundCluster,
      appEndpoints: builtEndpoints,
      primaryEndpoint: primaryEndpt,
      configDisplayData: configDisplay
    };
  }, [clusters, clusterId, appId]);

  const handleDeleteApp = () => {
    removeApplication(clusterId!, appId!);
    navigate(`/clusters/${clusterId}`);
  };

  if (!currentDeployment || !cluster) {
    return (
      <div className="p-6 space-y-4">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Application not found</AlertTitle>
          <AlertDescription>
            The application you are looking for does not exist or has been removed.
          </AlertDescription>
        </Alert>
        <Button variant="outline" asChild>
          <Link to={`/clusters/${clusterId}`}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Cluster
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" asChild>
            <Link to={`/clusters/${clusterId}`}>
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <h1 className="text-2xl font-bold">{currentDeployment.name}</h1>
        </div>
        <div className="space-x-2">
          <Button
            variant="outline"
            disabled={currentDeployment.status !== stateEnum.RUNNING}
            onClick={() => setShowCredentialsModal(true)}
          >
            <Key className="h-4 w-4 mr-2" /> Get Credentials
          </Button>
          <Button
            variant="outline"
            disabled={currentDeployment.status !== stateEnum.RUNNING}
            onClick={() => setShowUpdateConfigDialog(true)}
          >
            <Settings className="h-4 w-4 mr-2"/> Update Configuration
          </Button>
          <Button
            variant="destructive"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash className="h-4 w-4 mr-2" /> Delete Deployment
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {currentDeployment.status === stateEnum.FAILED && currentDeployment.errorMessage && (
        <Alert variant="destructive" className="mt-4">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Deployment Failed</AlertTitle>
          <AlertDescription>
            {currentDeployment.errorMessage}
          </AlertDescription>
        </Alert>
      )}

      {/* Overview Card - Now includes health check status */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-medium">Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row md:items-center gap-6">
            <div className="flex items-center justify-center h-16 w-16 rounded-lg bg-muted shrink-0">
              {currentDeployment.application.logo ? (
                <img
                  src={currentDeployment.application.logo}
                  alt={currentDeployment.application.name}
                  className="w-16 h-16 object-contain bg-white rounded-lg p-2"
                />
              ) : (
                <Server className="h-8 w-8 text-muted-foreground" />
              )}
            </div>
            <div className="flex-1 flex flex-col gap-2 justify-center">
              <div className="text-base font-semibold">{currentDeployment.application.name}</div>
              <p className="text-sm text-muted-foreground">{currentDeployment.application.description}</p>
              <div className="w-full mt-3">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-medium text-muted-foreground">Status:</span>
                    <StatusComponent
                      status={currentDeployment.status}
                      errorMessage={currentDeployment.errorMessage}
                    />
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-medium text-muted-foreground">Cluster:</span>
                    <span>{cluster.name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-medium text-muted-foreground">Deployed&nbsp;at:</span>
                    <span>
                      <Calendar className="h-4 w-4 mr-1 inline" />
                      {new Date(currentDeployment.deployedAt).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Embed the health check directly in the overview card when applicable */}
              {currentDeployment.status === stateEnum.RUNNING && primaryEndpoint && (
                <div className="mt-3 w-full">
                  <AppHealthCheck
                    endpoint={primaryEndpoint}
                    applicationName={currentDeployment.application.name}
                    deploymentStatus={currentDeployment.status}
                    interval={30000}
                    inline={false} // New prop to make it render inline in the overview card
                  />
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Access Points Card */}
      {currentDeployment.status === stateEnum.RUNNING && appEndpoints && appEndpoints.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {appEndpoints.map((endpoint) => (
            <Card key={endpoint.id} className="border-dashed flex flex-col">
              <CardHeader className="flex-1 pb-2">
                <CardTitle className="text-base">{endpoint.name}</CardTitle>
                <CardDescription className="line-clamp-2">{endpoint.description}</CardDescription>
              </CardHeader>
              <CardFooter className="pt-2">
                <Button asChild className="w-full">
                  <a href={endpoint.path} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Open {endpoint.name}
                  </a>
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      {/* Configuration Card */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-medium">Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {configDisplayData.length > 0 ? (
              <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                {configDisplayData.map(({ key, name, value }) => (
                  <div key={key} className="py-1 border-b">
                    <div className="font-medium truncate">{name}</div>
                    <div className="truncate text-sm text-muted-foreground">
                      {typeof value === 'boolean' 
                        ? value ? 'true' : 'false'
                        : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No configuration values set</p>
            )}
          </div>
        </CardContent>
        <CardFooter>
          <Button 
            variant="outline" 
            className="w-full"
            disabled={currentDeployment.status !== stateEnum.RUNNING}
            onClick={() => setShowUpdateConfigDialog(true)}
          >
            <Settings className="h-4 w-4 mr-2" /> Update Configuration
          </Button>
        </CardFooter>
      </Card>

      {/* Dialog components */}
      {showUpdateConfigDialog && (
        <UpdateConfigDialog
          open={showUpdateConfigDialog}
          onOpenChange={setShowUpdateConfigDialog}
          application={currentDeployment.application}
          currentConfig={currentDeployment.config}
          clusterId={clusterId!}
          appId={appId!}
        />
      )}

      {/* Credentials Modal */}
      <CredentialsModal
        open={showCredentialsModal}
        onOpenChange={setShowCredentialsModal}
        clusterId={clusterId!}
        deploymentId={appId!}
        applicationName={currentDeployment.application.name}
      />

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete {currentDeployment.application.name} from this cluster.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteApp}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default DeploymentDetails;
