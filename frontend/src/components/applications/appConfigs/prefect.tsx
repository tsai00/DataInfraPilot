
import { Application } from "@/types";
import { applications } from "@/data/applications";

const prefectApp: Application = applications.find(a => a.short_name === "prefect")!;

const prefectRecommendedResources = {
  nodes: "2",
  ram: "2 GB",
  cpu: "1 vCPU",
};

export function validatePrefectConfig(config: Record<string, any>): true | string[] {
  const missing: string[] = [];
  
  if (!config.deployment_name) {
    missing.push("Deployment Name");
  }
  
  prefectApp.configOptions.forEach((option) => {
    if (option.required && (config[option.id] === undefined || config[option.id] === "")) {
      missing.push(option.name);
    }
  });
  return missing.length > 0 ? missing : true;
}

const PrefectDeployConfig = {
  configOptions: prefectApp.configOptions,
  validateConfig: validatePrefectConfig,
  appRecommendedResources: prefectRecommendedResources
};

export default PrefectDeployConfig;
