
import { Application } from "@/types";
import { applications } from "@/data/applications";

// 1. Find the Airflow application definition from centralized data
const airflowApp: Application =
  applications.find(a => a.short_name === "airflow")!;

// 2. Airflow recommended resources row
const airflowRecommendedResources = {
  nodes: "3",
  ram: "8 GB",
  cpu: "4 vCPU",
};

const volumeRequirements = {
  name: "airflow-logs",
  defaultSize: 50,
  description: "For Airflow logs"
};

// Enhanced config options with custom image support - moved to beginning
const enhancedConfigOptions = [
  {
    id: "use_custom_image",
    name: "Use Custom Image",
    type: "boolean" as const,
    description: "Enable to use a custom Airflow image from a private registry",
    required: false,
    default: false
  },
  {
    id: "private_registry_url",
    name: "Private Registry URL",
    type: "text" as const,
    description: "URL of the private container registry (e.g., registry.company.com/airflow)",
    required: false,
    conditional: {
      field: "use_custom_image",
      value: true
    }
  },
  {
    id: "private_registry_username",
    name: "Registry Username",
    type: "text" as const,
    description: "Username for private registry authentication",
    required: false,
    conditional: {
      field: "use_custom_image",
      value: true
    }
  },
  {
    id: "private_registry_password",
    name: "Registry Password",
    type: "text" as const,
    description: "Password for private registry authentication",
    required: false,
    conditional: {
      field: "use_custom_image",
      value: true
    }
  },
  {
    id: "private_registry_image_tag",
    name: "Image Tag",
    type: "text" as const,
    description: "Tag of the custom Airflow image (e.g., latest, v2.8.0)",
    required: false,
    conditional: {
      field: "use_custom_image",
      value: true
    }
  },
  ...airflowApp.configOptions
];

// 3. Airflow config validation (known fields + DAG repo + custom image)
export function validateAirflowConfig(config: Record<string, any>): true | string[] {
  const missing: string[] = [];
  
  // Check for deployment name
  if (!config.deployment_name) {
    missing.push("Deployment Name");
  }
  
  enhancedConfigOptions.forEach((option) => {
    // Skip conditional fields that aren't required based on their condition
    if (option.conditional) {
      if (config[option.conditional.field] !== option.conditional.value) {
        return;
      }
    }
    
    // Skip version field if custom image is enabled
    if (option.id === "version" && config.use_custom_image) {
      return;
    }
    
    // Skip SSH key if repo is not private
    if (option.id === "airflowSshKey" && !config.airflowRepoPrivate) {
      return;
    }
    
    // For custom image, require registry URL if enabled
    if (config.use_custom_image && option.id === "private_registry_url" && !config[option.id]) {
      missing.push(option.name);
      return;
    }
    
    if (option.required && (config[option.id] === undefined || config[option.id] === "")) {
      missing.push(option.name);
    }
  });
  
  return missing.length > 0 ? missing : true;
}

// 4. Unified deploy config for Airflow
const AirflowDeployConfig = {
  configOptions: enhancedConfigOptions,
  validateConfig: validateAirflowConfig,
  appRecommendedResources: airflowRecommendedResources,
  volumeRequirements: volumeRequirements
};

export default AirflowDeployConfig;
