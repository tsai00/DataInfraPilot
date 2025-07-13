import React from "react";
import { AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { stateEnum } from "@/types/stateEnum";
import { useHealthCheck } from "@/hooks/useHealthCheck.ts";

interface AppHealthCheckProps {
  endpoint: string;
  applicationName: string;
  deploymentStatus: stateEnum;
  interval?: number; // polling interval in milliseconds
  inline?: boolean; // whether to render inline in another component or as a standalone card
}

const AppHealthCheck: React.FC<AppHealthCheckProps> = ({
  endpoint,
  applicationName,
  deploymentStatus,
  interval = 30000,
  inline = false,
}) => {
  const { healthStatus, lastChecked, errorMessage, shouldCheckHealth } = useHealthCheck({
    endpoint,
    applicationName,
    deploymentStatus,
    interval,
  });

  if (!shouldCheckHealth) {
    return null;
  }

  // Inline version for embedding in other components
  if (inline) {
    return (
      <div className="flex items-center gap-1 text-sm">
        {healthStatus === "checking" && (
          <Loader2 className="h-4 w-4 text-amber-500 animate-spin" />
        )}
        {healthStatus === "healthy" && (
          <CheckCircle className="h-4 w-4 text-green-500" />
        )}
        {healthStatus === "unhealthy" && (
          <TooltipProvider delayDuration={200}>
            <Tooltip>
              <TooltipTrigger asChild>
                <AlertCircle className="h-4 w-4 text-red-500" />
              </TooltipTrigger>
              <TooltipContent>
                <p>{errorMessage || "Application endpoint is not responding"}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
        {lastChecked && (
          <span className="text-muted-foreground text-xs">
            ({lastChecked.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
          </span>
        )}
      </div>
    );
  }

  // Standalone card version
  return (
    <div className="flex items-center justify-between border rounded-md p-3 bg-background/50">
      <div className="flex items-center space-x-2">
        {healthStatus === "checking" && (
          <Loader2 className="h-5 w-5 text-amber-500 animate-spin" />
        )}
        {healthStatus === "healthy" && (
          <CheckCircle className="h-5 w-5 text-green-500" />
        )}
        {healthStatus === "unhealthy" && (
          <TooltipProvider delayDuration={200}>
            <Tooltip>
              <TooltipTrigger asChild>
                <AlertCircle className="h-5 w-5 text-red-500" />
              </TooltipTrigger>
              <TooltipContent>
                <p>{errorMessage || "Application endpoint is not responding"}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
        <span className="font-medium">
          {healthStatus === "checking" && "Checking application..."}
          {healthStatus === "healthy" && "Application is ready"}
          {healthStatus === "unhealthy" && "Application is not responsive (if it's a first deployment, please wait few minutes)"}
        </span>
      </div>
      {lastChecked && (
        <span className="text-xs text-muted-foreground">
          Last checked: {lastChecked.toLocaleTimeString()}
        </span>
      )}
    </div>
  );
};

export default AppHealthCheck;
