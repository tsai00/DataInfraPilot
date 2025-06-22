import { useState, useEffect } from "react";
import { stateEnum } from "@/types/stateEnum";
import { API_BASE_URL } from "@/services/apiClient";

interface UseHealthCheckProps {
  endpoint: string;
  applicationName: string;
  deploymentStatus: stateEnum;
  interval?: number;
}

export type HealthStatus = "checking" | "healthy" | "unhealthy" | "pending";

export const useHealthCheck = ({
  endpoint,
  applicationName,
  deploymentStatus,
  interval = 30000,
}: UseHealthCheckProps) => {
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
        // Add a timestamp to prevent caching
        const urlWithTimestamp = `${endpoint}${endpoint.includes('?') ? '&' : '?'}_t=${Date.now()}`;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        const response = await fetch(`${API_BASE_URL}/deployments/proxy-health-check?target_url=${encodeURIComponent(urlWithTimestamp)}`, {
          method: 'GET',
          signal: controller.signal,
          mode: 'cors',
        });

        clearTimeout(timeoutId);

        console.log("Performed health check for app " + applicationName + "(" + endpoint + "): " + response.status);

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

  return {
    healthStatus,
    lastChecked,
    errorMessage,
    shouldCheckHealth,
  };
};
