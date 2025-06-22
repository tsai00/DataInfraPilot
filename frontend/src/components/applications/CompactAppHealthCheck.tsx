import React from "react";
import { AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { stateEnum } from "@/types/stateEnum";
import { useHealthCheck } from "@/hooks/useHealthCheck.ts";

interface CompactAppHealthCheckProps {
  endpoint: string;
  applicationName: string;
  deploymentStatus: stateEnum;
  interval?: number;
}

const CompactAppHealthCheck: React.FC<CompactAppHealthCheckProps> = ({
  endpoint,
  applicationName,
  deploymentStatus,
  interval = 60000,
}) => {
  const { healthStatus, lastChecked, shouldCheckHealth } = useHealthCheck({
    endpoint,
    applicationName,
    deploymentStatus,
    interval,
  });

  if (!shouldCheckHealth) {
    return <span className="text-muted-foreground text-sm">N/A</span>;
  }

  const getStatusText = () => {
    switch (healthStatus) {
      case "checking":
        return "Checking...";
      case "healthy":
        return "Healthy";
      case "unhealthy":
        return "Unhealthy";
      default:
        return "Pending";
    }
  };

  const getStatusIcon = () => {
    switch (healthStatus) {
      case "checking":
        return <Loader2 className="h-3 w-3 text-amber-500 animate-spin" />;
      case "healthy":
        return <CheckCircle className="h-3 w-3 text-green-500" />;
      case "unhealthy":
        return <AlertCircle className="h-3 w-3 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="flex items-center gap-2 text-sm">
      {getStatusIcon()}
      <span className="font-medium">{getStatusText()}</span>
      {lastChecked && (
        <span className="text-muted-foreground text-xs">
          {lastChecked.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      )}
    </div>
  );
};

export default CompactAppHealthCheck;
