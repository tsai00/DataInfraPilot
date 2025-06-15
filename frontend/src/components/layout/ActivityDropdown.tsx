
import React from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useClusterStore } from "@/store";

const ActivityDropdown: React.FC = () => {
  const { clusters, domainActivities } = useClusterStore();
  
  // Get recent activities from clusters, deployed apps, and domains
  const recentActivities = [
    ...clusters
      .filter(c => c.status === "creating" || c.status === "updating" || c.status === "deleting")
      .map(c => ({
        type: "cluster",
        id: c.id,
        name: c.name,
        status: c.status,
        time: new Date(c.created).toISOString(),
        message: `Cluster "${c.name}" is ${c.status}`,
      })),
    ...clusters.flatMap(c => 
      c.deployments
        .filter(deployment => deployment.status === "deploying" || deployment.status === "updating")
        .map(deployment => ({
          type: "deployment",
          id: deployment.id,
          clusterId: c.id,
          name: deployment.application.name,
          status: deployment.status,
          time: new Date(deployment.deployedAt).toISOString(),
          message: `Application "${deployment.application.name}" is ${deployment.status} on ${c.name}`,
        }))
    ),
    // Add domain activities
    // ...domainActivities.map(activity => ({
    //   type: "domain",
    //   id: activity.id,
    //   name: activity.domainName,
    //   status: activity.action,
    //   time: activity.timestamp,
    //   message: `${activity.action === "creating" || activity.action === "deleting" ? 
    //            `Cluster "${activity.domainName}" is ${activity.action}` :
    //            activity.action === "deploying" || activity.action === "deployed" ?
    //            `Application ${activity.domainName}` :
    //            `Domain "${activity.domainName}" ${activity.action}`}`,
    // }))
  ].sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
  .slice(0, 10);

  const hasActiveNotifications = recentActivities.length > 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {hasActiveNotifications && (
            <span className="absolute top-1 right-1.5 w-2 h-2 bg-red-500 rounded-full"></span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel>Recent Activity</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          {recentActivities.length > 0 ? (
            recentActivities.map((activity) => (
              <DropdownMenuItem key={`${activity.type}-${activity.id}`} className="py-2 flex flex-col items-start">
                <span className="font-medium">{activity.message}</span>
                <span className="text-xs text-muted-foreground">
                  {new Date(activity.time).toLocaleString()}
                </span>
              </DropdownMenuItem>
            ))
          ) : (
            <DropdownMenuItem disabled>No recent activity</DropdownMenuItem>
          )}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default ActivityDropdown;
