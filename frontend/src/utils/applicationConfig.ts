import { Application, ConfigOption } from "@/types";

/**
 * Generic application configuration utilities
 */

export function validateApplicationConfig(
  app: Application,
  config: Record<string, any>
): true | string[] {
  const missing: string[] = [];

  // Validate all required config options
  app.configOptions.forEach((option) => {
    if (option.required && (config[option.id] === undefined || config[option.id] === "")) {
      missing.push(option.name);
    }
  });

  // Special validation for Airflow DAG repository URL
  if (app.short_name === "airflow" && config.dags_repository) {
    const repoUrl = config.dags_repository;
    const validGitUrlPattern = /^(https?:\/\/|git@)/;

    if (!validGitUrlPattern.test(repoUrl)) {
      missing.push("Valid DAGs Git Repository URL (must start with https://, http://, or git@)");
    }
  }

  // Validation for custom image config in Airflow (if using enhanced config)
  if (app.short_name === "airflow" && config.use_custom_image) {
    if (!config.custom_image_registry_url) {
      missing.push("Private Registry URL");
    }
    if (!config.custom_image_tag) {
      missing.push("Image Tag");
    }
  }

  return missing.length > 0 ? missing : true;
}

export function getInitialConfig(app: Application): Record<string, any> {
  return app.configOptions.reduce((acc, option) => {
    if (option.default !== undefined) {
      acc[option.id] = option.default;
    }
    return acc;
  }, {} as Record<string, any>);
}

export function shouldShowConfigOption(
  option: ConfigOption,
  config: Record<string, any>
): boolean {
  if (option.conditional) {
    const { field, value } = option.conditional;
    return config[field] === value;
  }

  return true;
}

export function getAppRecommendedResources(app: Application) {
  return app.recommendedResources || {
    nodes: "1",
    ram: "1 GB",
    cpu: "1 vCPU"
  };
}

export function getAppVolumeRequirements(app: Application) {
  return app.volumeRequirements || [];
}