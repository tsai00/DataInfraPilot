import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Cloud,
  Database,
  Plus,
  Server,
  Cpu,
  DollarSign,
  Globe,
  Settings,
  ArrowRight,
  HardDrive,
  Euro,
  Package
} from "lucide-react";
import { useClusterStore } from "@/store";
import CreateClusterModal from "@/components/clusters/CreateClusterModal";
import { stateEnum } from "@/types/stateEnum";
import { calculateTotalInfrastructureCost } from "@/utils/costCalculations";

const Dashboard: React.FC = () => {
  const { clusters, volumes, providers } = useClusterStore();
  const [showCreateCluster, setShowCreateCluster] = React.useState(false);

  const totalClusters = clusters.length;
  const runningClusters = clusters.filter((c) => c.status === stateEnum.RUNNING).length;
  const totalDeployments = clusters.reduce(
    (count, cluster) => count + cluster.deployments.length,
    0
  );
  
  // Calculate total nodes including control plane
  const totalNodes = clusters.reduce(
    (count, cluster) =>
      count +
      cluster.nodePools.reduce((poolCount, pool) => poolCount + pool.count, 0) +
      cluster.controlPlane.count,
    0
  );

  // Calculate total monthly cost using unified function
  const totalCost = calculateTotalInfrastructureCost(clusters, volumes, providers);

  // Quick action cards
  const quickActions = [
    {
      title: "Create Cluster",
      description: "Deploy a new Kubernetes cluster",
      icon: Cloud,
      action: () => setShowCreateCluster(true),
      color: "bg-blue-100",
      iconColor: "text-k8s-blue"
    },
    {
      title: "View Clusters",
      description: "Manage your existing clusters",
      icon: Server,
      link: "/clusters",
      color: "bg-purple-100",
      iconColor: "text-purple-600"
    },
    {
      title: "View Deployments",
      description: "Overview of all deployments",
      icon: Package,
      link: "/deployments",
      color: "bg-green-100",
      iconColor: "text-green-600"
    }
  ];

  return (
    <>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor and manage your Kubernetes infrastructure
          </p>
        </div>
        <Button onClick={() => setShowCreateCluster(true)}>
          <Plus className="mr-2 h-4 w-4" /> Create Cluster
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  Total Clusters
                </p>
                <h3 className="text-2xl font-bold">{totalClusters}</h3>
              </div>
              <div className="bg-blue-100 p-3 rounded-full">
                <Cloud className="h-6 w-6 text-k8s-blue" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  Total Deployments
                </p>
                <h3 className="text-2xl font-bold">{totalDeployments}</h3>
              </div>
              <div className="bg-green-100 p-3 rounded-full">
                <Database className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  Total Nodes
                </p>
                <h3 className="text-2xl font-bold">{totalNodes}</h3>
              </div>
              <div className="bg-purple-100 p-3 rounded-full">
                <Server className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  Monthly Cost
                </p>
                <h3 className="text-2xl font-bold">
                  {totalCost.monthly.toFixed(2)} €
                </h3>
              </div>
              <div className="bg-amber-100 p-3 rounded-full">
                <Euro className="h-6 w-6 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <h2 className="text-2xl font-bold mb-4">Quick Actions</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {quickActions.map((action, index) => (
          <Card key={index} className="hover:shadow-md transition-all">
            {action.link ? (
              <Link to={action.link} className="block h-full">
                <CardContent className="p-6 h-full flex flex-col">
                  <div className={`${action.color} p-3 rounded-full mb-4 self-start`}>
                    <action.icon className={`h-6 w-6 ${action.iconColor}`} />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-bold mb-1">{action.title}</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      {action.description}
                    </p>
                  </div>
                  <div className="flex justify-end">
                    <ArrowRight className="h-5 w-5 text-muted-foreground" />
                  </div>
                </CardContent>
              </Link>
            ) : (
              <CardContent 
                className="p-6 cursor-pointer h-full flex flex-col" 
                onClick={action.action}
              >
                <div className={`${action.color} p-3 rounded-full mb-4 self-start`}>
                  <action.icon className={`h-6 w-6 ${action.iconColor}`} />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold mb-1">{action.title}</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    {action.description}
                  </p>
                </div>
                <div className="flex justify-end">
                  <ArrowRight className="h-5 w-5 text-muted-foreground" />
                </div>
              </CardContent>
            )}
          </Card>
        ))}
      </div>

      <CreateClusterModal 
        open={showCreateCluster} 
        onClose={() => setShowCreateCluster(false)} 
      />
    </>
  );
};

export default Dashboard;
