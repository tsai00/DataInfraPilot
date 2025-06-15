import React, { useState, useEffect } from "react";
import { AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { stateEnum } from "@/types/stateEnum";
import { API_BASE_URL } from "@/services/apiClient";

interface CompactAppHealthCheckProps {
  endpoint: string;
  applicationName: string;
  deploymentStatus: stateEnum;
  interval?: number;
}

type HealthStatus = "checking" | "healthy" | "unhealthy" | "pending";

const CompactAppHealthCheck: React.FC<CompactAppHealthCheckProps> = ({
  endpoint,
  applicationName,
  deploymentStatus,
  interval = 60000,
}) => {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>("pending");
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const shouldCheckHealth = deploymentStatus === stateEnum.RUNNING;

  useEffect(() => {
    if (!shouldCheckHealth) {
      setHealthStatus("pending");
      return;
    }

    const checkHealth = async () => {
      if (!endpoint) return;

      setHealthStatus("checking");

      try {
        const urlWithTimestamp = `${endpoint}${endpoint.includes('?') ? '&' : '?'}_t=${Date.now()}`;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        const response = await fetch(`${API_BASE_URL}/deployments/proxy-health-check?target_url=${urlWithTimestamp}`, {
          method: 'GET',
          signal: controller.signal,
          mode: 'cors',
        });

        clearTimeout(timeoutId);

        console.log("Perfomed health check for app " + applicationName + "(" + endpoint + "): " + response.status)

        if (!response.ok) {
          setHealthStatus("unhealthy");
          setErrorMessage("Service unavailable");
          setLastChecked(new Date());
          return;
        }

        setHealthStatus("healthy");
        setErrorMessage(null);
      } catch (error) {
        console.error("Health check error:", error);

        if (error instanceof DOMException && error.name === "AbortError") {
          setErrorMessage("Request timed out");
        } else if (error instanceof TypeError && error.message.includes("NetworkError")) {
          setErrorMessage("Network error - possibly CORS related");
        } else {
          setErrorMessage(
            error instanceof Error
              ? error.message
              : "Unable to connect to application"
          );
        }

        setHealthStatus("unhealthy");
      }

      setLastChecked(new Date());
    };

    checkHealth();
    const intervalId = setInterval(checkHealth, interval);

    return () => {
      clearInterval(intervalId);
    };
  }, [applicationName, endpoint, interval, shouldCheckHealth]);

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
