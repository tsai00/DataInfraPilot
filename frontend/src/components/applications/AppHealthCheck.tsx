
import React, { useState, useEffect } from "react";
import { AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { stateEnum } from "@/types/stateEnum";
import {API_BASE_URL} from "@/services/apiClient";

interface AppHealthCheckProps {
  endpoint: string;
  applicationName: string;
  deploymentStatus: stateEnum;
  interval?: number; // polling interval in milliseconds
  inline?: boolean; // whether to render inline in another component or as a standalone card
}

// Health check states
type HealthStatus = "checking" | "healthy" | "unhealthy" | "pending";

const AppHealthCheck: React.FC<AppHealthCheckProps> = ({
  endpoint,
  applicationName,
  deploymentStatus,
  interval = 30000, // default to checking every 30 seconds
  inline = false, // default to standalone card
}) => {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>("pending");
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Only run health checks when deployment status is RUNNING
  const shouldCheckHealth = deploymentStatus === stateEnum.RUNNING;

  useEffect(() => {
    if (!shouldCheckHealth) {
      setHealthStatus("pending");
      return;
    }

    // Function to check endpoint health
    const checkHealth = async () => {
      if (!endpoint) return;
      
      setHealthStatus("checking");
      
      try {
        // Add a timestamp to prevent caching
        const urlWithTimestamp = `${endpoint}${endpoint.includes('?') ? '&' : '?'}_t=${Date.now()}`;
        
        // Use a timeout to avoid hanging checks
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
        
        const response = await fetch(`${API_BASE_URL}/deployments/proxy-health-check?target_url=${urlWithTimestamp}`, {
          method: 'GET',
          signal: controller.signal,
          mode: 'cors', // Use no-cors mode since we may not have access to cross-origin responses
        });
        
        clearTimeout(timeoutId);

        console.log("Perfomed health check for app " + applicationName + "(" + endpoint + "): " + response.status)
        
        // Check if response is ok (status 200-299)
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
        
        // Check for specific abort errors
        if (error instanceof DOMException && error.name === "AbortError") {
          setErrorMessage("Request timed out");
        } else if (error instanceof TypeError && error.message.includes("NetworkError")) {
          // CORS errors will appear as network errors
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

    // Run health check immediately and then periodically
    checkHealth();
    const intervalId = setInterval(checkHealth, interval);

    return () => {
      clearInterval(intervalId);
    };
  }, [applicationName, endpoint, interval, shouldCheckHealth]);

  // If deployment isn't running, don't show the health check
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
          {healthStatus === "unhealthy" && applicationName === "airflow" && "Application is not responsive1"}
          {healthStatus === "unhealthy" && "Application is not responsive"}
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
