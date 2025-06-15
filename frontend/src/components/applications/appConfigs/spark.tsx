
import { Application } from "@/types";
import { applications } from "@/data/applications";

const sparkApp: Application = applications.find(a => a.short_name === "spark")!;

const sparkRecommendedResources = {
  nodes: "2",
  ram: "2 GB",
  cpu: "1 vCPU",
};

export function validateSparkConfig(config: Record<string, any>): true | string[] {
  const missing: string[] = [];
  
  // Check for deployment name
  if (!config.deployment_name) {
    missing.push("Deployment Name");
  }
  
  sparkApp.configOptions.forEach((option) => {
    if (option.required && (config[option.id] === undefined || config[option.id] === "")) {
      missing.push(option.name);
    }
  });
  return missing.length > 0 ? missing : true;
}

const SparkDeployConfig = {
  configOptions: sparkApp.configOptions,
  validateConfig: validateSparkConfig,
  appRecommendedResources: sparkRecommendedResources
};

export default SparkDeployConfig;
