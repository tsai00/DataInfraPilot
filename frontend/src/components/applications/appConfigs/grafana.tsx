
import { Application } from "@/types";
import { applications } from "@/data/applications";

// 1. Find the Grafana application definition from centralized data
const grafanaApp: Application = applications.find(a => a.short_name === "grafana")!;

// 2. Grafana recommended resources row
const grafanaRecommendedResources = {
  nodes: "2",
  ram: "2 GB",
  cpu: "1 vCPU",
};

// 3. Grafana config validation
export function validateGrafanaConfig(config: Record<string, any>): true | string[] {
  const missing: string[] = [];
  
  // Check for deployment name
  if (!config.deployment_name) {
    missing.push("Deployment Name");
  }
  
  grafanaApp.configOptions.forEach((option) => {
    if (option.required && (config[option.id] === undefined || config[option.id] === "")) {
      missing.push(option.name);
    }
  });
  return missing.length > 0 ? missing : true;
}

// 4. Unified deploy config for Grafana
const GrafanaDeployConfig = {
  configOptions: grafanaApp.configOptions,
  validateConfig: validateGrafanaConfig,
  appRecommendedResources: grafanaRecommendedResources
};

export default GrafanaDeployConfig;
