import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Database,
  Server,
  ExternalLink,
  Clock,
  Package,
  Activity
} from "lucide-react";
import { useClusterStore } from "@/store";
import { stateEnum } from "@/types/stateEnum";
import { formatDistanceToNow } from "date-fns";
import StatusComponent from "@/components/StatusComponent";
import AppHealthCheck from "@/components/applications/AppHealthCheck";
import { AccessEndpointType, Deployment } from "@/types";

const Deployments: React.FC = () => {
  const { clusters } = useClusterStore();

  // Get all deployments from all clusters
  const allDeployments = clusters.flatMap(cluster => 
    cluster.deployments.map(deployment => ({
      ...deployment,
      clusterName: cluster.name,
      clusterId: cluster.id,
      clusterStatus: cluster.status
    }))
  );

  const totalDeployments = allDeployments.length;
  const runningDeployments = allDeployments.filter(d => d.status === stateEnum.RUNNING).length;
  const deployingDeployments = allDeployments.filter(d => d.status === stateEnum.DEPLOYING).length;
  const failedDeployments = allDeployments.filter(d => d.status === stateEnum.FAILED).length;

  // Helper function to get the primary endpoint for health check
  const getPrimaryEndpoint = (deployment: Deployment) => {
    if (!deployment.accessEndpoints || deployment.accessEndpoints.length === 0) {
      return null;
    }

    const foundCluster = clusters.find((c) => c.id === deployment['clusterId']);
    
    // Find the first endpoint to use for health check
    const primaryEndpoint = deployment.accessEndpoints[0];
    
    let primaryEndpointFull;
    // Construct the URL based on access type
    switch (primaryEndpoint.access_type) {
      case AccessEndpointType.SUBDOMAIN:
        // Format: https://subdomain.domain.com/
        primaryEndpointFull = `https://${primaryEndpoint.value}.${foundCluster.access_ip}`;
        break;
      case AccessEndpointType.DOMAIN_PATH:
        // Format: https://domain.com/path
        primaryEndpointFull = `https://${foundCluster.domainName}${primaryEndpoint.value}`;
        break;
      case AccessEndpointType.CLUSTER_IP_PATH:
      default:
        // Format: http://ip/path
        primaryEndpointFull = `http://${foundCluster.access_ip}${primaryEndpoint.value}`;
        break;
    }

    return primaryEndpointFull;
  };

  return (
    <>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">All Deployments</h1>
          <p className="text-muted-foreground">
            Overview of all applications deployed across your clusters
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  Total Deployments
                </p>
                <h3 className="text-2xl font-bold">{totalDeployments}</h3>
              </div>
              <div className="bg-blue-100 p-3 rounded-full">
                <Package className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  Running
                </p>
                <h3 className="text-2xl font-bold">{runningDeployments}</h3>
              </div>
              <div className="bg-green-100 p-3 rounded-full">
                <Activity className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  Deploying
                </p>
                <h3 className="text-2xl font-bold">{deployingDeployments}</h3>
              </div>
              <div className="bg-blue-100 p-3 rounded-full">
                <Clock className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  Failed
                </p>
                <h3 className="text-2xl font-bold">{failedDeployments}</h3>
              </div>
              <div className="bg-red-100 p-3 rounded-full">
                <Database className="h-6 w-6 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Deployments Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Deployments</CardTitle>
          <CardDescription>
            Complete list of all applications deployed across your clusters
          </CardDescription>
        </CardHeader>
        <CardContent>
          {allDeployments.length === 0 ? (
            <div className="text-center py-8">
              <Package className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No deployments found</h3>
              <p className="text-muted-foreground mb-4">
                You haven't deployed any applications yet.
              </p>
              <Button asChild>
                <Link to="/clusters">Go to Clusters</Link>
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-center">Application</TableHead>
                  <TableHead className="text-center">Cluster</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-center">Health</TableHead>
                  <TableHead className="text-center">Deployed</TableHead>
                  <TableHead className="text-center">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {allDeployments.map((deployment) => {
                  const primaryEndpoint = getPrimaryEndpoint(deployment);
                  
                  return (
                    <TableRow key={`${deployment.clusterId}-${deployment.id}`}>
                      <TableCell className="text-center">
                        <div className="flex items-center gap-3 justify-center">
                          <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center border">
                            <img 
                              src={deployment.application?.logo} 
                              alt={deployment.application?.name}
                              className="w-6 h-6 object-contain"
                              onError={(e) => {
                                const target = e.target as HTMLImageElement;
                                target.style.display = 'none';
                                const fallback = target.parentElement?.querySelector('.fallback-icon') as HTMLElement;
                                if (fallback) fallback.style.display = 'block';
                              }}
                            />
                            <Database className="h-4 w-4 text-blue-600 fallback-icon hidden" />
                          </div>
                          <div>
                            <div className="font-medium">{deployment.name}</div>
                            <div className="text-sm text-muted-foreground">
                              {deployment.application?.name}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex items-center gap-2 justify-center">
                          <Server className="h-4 w-4 text-muted-foreground" />
                          <span>{deployment.clusterName}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex justify-center">
                          <StatusComponent status={deployment.status} errorMessage={deployment.errorMessage}/>
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex justify-center">
                          {primaryEndpoint ? (
                            <AppHealthCheck
                              endpoint={primaryEndpoint}
                              applicationName={deployment.application?.name || deployment.name}
                              deploymentStatus={deployment.status}
                              inline={true}
                              interval={60000} // Check every minute for table view
                            />
                          ) : (
                            <span className="text-muted-foreground text-sm">No endpoint</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="text-sm">
                          {formatDistanceToNow(new Date(deployment.deployedAt), { addSuffix: true })}
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex justify-center">
                          <Button variant="outline" size="sm" asChild>
                            <Link 
                              to={`/clusters/${deployment.clusterId}/deployments/${deployment.id}`}
                              className="flex items-center gap-2"
                            >
                              <ExternalLink className="h-4 w-4" />
                              View Details
                            </Link>
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
};

export default Deployments;
