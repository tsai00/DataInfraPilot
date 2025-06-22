
import React, { useState, useEffect } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Info } from "lucide-react";
import { Cluster, AccessEndpoint, AccessEndpointConfig, AccessEndpointType } from "@/types";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

interface AccessConfigStepProps {
  cluster: Cluster;
  accessEndpoints: AccessEndpoint[];
  endpointConfigs: AccessEndpointConfig[];
  setEndpointConfigs: (configs: AccessEndpointConfig[]) => void;
  applicationConfig?: Record<string, any>; // Add config to filter endpoints
}

const AccessConfigStep: React.FC<AccessConfigStepProps> = ({
  cluster,
  accessEndpoints,
  endpointConfigs,
  setEndpointConfigs,
  applicationConfig = {},
}) => {
  const hasDomain = !!cluster?.domainName;
  const [activeTab, setActiveTab] = useState<string>("0");
  const [enabledEndpoints, setEnabledEndpoints] = useState<Record<string, boolean>>({});

  // Filter endpoints based on application configuration
  const filteredEndpoints = accessEndpoints.filter(endpoint => {
    // For Airflow, only show Flower UI if using CeleryExecutor
    if (endpoint.name === 'flower-ui') {
      const isCeleryExecutor = applicationConfig.executor === 'CeleryExecutor';
      const isFlowerEnabled = applicationConfig.flower_enabled === true;
      return isCeleryExecutor && isFlowerEnabled;
    }
    return true;
  });

  useEffect(() => {
    // Initialize enabled state for optional endpoints
    const initialEnabledState: Record<string, boolean> = {};
    filteredEndpoints.forEach((endpoint) => {
      initialEnabledState[endpoint.name] = endpoint.required ||
        endpointConfigs.some(config => config.name === endpoint.name);
    });
    setEnabledEndpoints(initialEnabledState);
  }, [filteredEndpoints, endpointConfigs]);

  const updateEndpointConfig = (name: string, field: keyof AccessEndpointConfig, value: string) => {
    console.log(`Updating endpoint config for ${name}: ${field} = ${value}`);

    const updatedConfigs = [...endpointConfigs];
    const configIndex = updatedConfigs.findIndex(config => config.name === name);

    if (configIndex >= 0) {
      updatedConfigs[configIndex] = {
        ...updatedConfigs[configIndex],
        [field]: value
      };
      console.log(`Updated existing config:`, updatedConfigs[configIndex]);
    } else {
      // Find the default configuration from accessEndpoints
      const endpoint = filteredEndpoints.find(e => e.name === name);
      if (endpoint) {
        const newConfig = {
          name,
          access_type: field === 'access_type' ? value as AccessEndpointType : endpoint.default_access,
          value: field === 'value' ? value : endpoint.default_value
        };
        updatedConfigs.push(newConfig);
        console.log(`Created new config:`, newConfig);
      }
    }

    console.log(`All endpoint configs:`, updatedConfigs);
    setEndpointConfigs(updatedConfigs);
  };

  const toggleEndpoint = (name: string, enabled: boolean) => {
    setEnabledEndpoints(prev => ({
      ...prev,
      [name]: enabled
    }));

    if (!enabled) {
      // Remove the endpoint from configs when disabled
      const updatedConfigs = endpointConfigs.filter(config => config.name !== name);
      setEndpointConfigs(updatedConfigs);
    } else {
      // Add the endpoint with default values when enabled
      const endpoint = filteredEndpoints.find(e => e.name === name);
      if (endpoint) {
        const newConfig: AccessEndpointConfig = {
          name,
          access_type: endpoint.default_access === AccessEndpointType.DOMAIN_PATH ? AccessEndpointType.DOMAIN_PATH : (hasDomain ? AccessEndpointType.SUBDOMAIN : AccessEndpointType.CLUSTER_IP_PATH),
          value: endpoint.default_value
        };
        setEndpointConfigs([...endpointConfigs, newConfig]);
      }
    }
  };

  const getEndpointConfig = (name: string): AccessEndpointConfig | undefined => {
    return endpointConfigs.find(config => config.name === name);
  };

  return (
    <div className="space-y-6 py-4">
      <div className="space-y-4">
        <h3 className="font-medium">Configure Application Access</h3>


        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
            {filteredEndpoints.map((endpoint, index) => (
              <TabsTrigger key={endpoint.name} value={index.toString()}>
                {endpoint.description}
              </TabsTrigger>
            ))}
          </TabsList>

          {filteredEndpoints.map((endpoint, index) => (
            <TabsContent key={endpoint.name} value={index.toString()} className="mt-4">
              <EndpointAccessForm
                endpoint={endpoint}
                config={getEndpointConfig(endpoint.name)}
                hasDomain={hasDomain}
                cluster={cluster}
                onChange={(field, value) => updateEndpointConfig(endpoint.name, field, value)}
                enabled={enabledEndpoints[endpoint.name] || false}
                onToggleEnabled={(enabled) => toggleEndpoint(endpoint.name, enabled)}
              />
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </div>
  );
};

interface EndpointAccessFormProps {
  endpoint: AccessEndpoint;
  config?: AccessEndpointConfig;
  hasDomain: boolean;
  cluster: Cluster;
  onChange: (field: keyof AccessEndpointConfig, value: string) => void;
  enabled: boolean;
  onToggleEnabled: (enabled: boolean) => void;
}

const EndpointAccessForm: React.FC<EndpointAccessFormProps> = ({
  endpoint,
  config,
  hasDomain,
  cluster,
  onChange,
  enabled,
  onToggleEnabled
}) => {
  const accessType = config?.access_type || endpoint.default_access;
  const value = config?.value || endpoint.default_value;

  if (!enabled && !endpoint.required) {
    return (
      <div className="border rounded-lg p-4 bg-secondary/10">
        <div className="flex items-center space-x-2">
          <Checkbox
            id={`enable-${endpoint.name}`}
            checked={enabled}
            onCheckedChange={(checked) => onToggleEnabled(!!checked)}
          />
          <Label htmlFor={`enable-${endpoint.name}`}>Enable {endpoint.description}</Label>
        </div>
      </div>
    );
  }

  // Get the raw input value (what user types)
  const getInputValue = () => {
    if (accessType === AccessEndpointType.SUBDOMAIN) {
      // For subdomain: show only the subdomain part, no domain, no slashes
      return value.includes('.') ? value.split('.')[0] : value.replace(/^\/+/, '');
    } else {
      // For paths: show without the leading slash (since it's in the prefix)
      return value.replace(/^\/+/, '');
    }
  };

  const inputValue = getInputValue();

  return (
    <div className="border rounded-lg p-4 bg-secondary/10">
      {!endpoint.required && (
        <div className="flex items-center space-x-2 mb-4">
          <Checkbox
            id={`enable-${endpoint.name}`}
            checked={enabled}
            onCheckedChange={(checked) => onToggleEnabled(!!checked)}
          />
          <Label htmlFor={`enable-${endpoint.name}`}>Enable {endpoint.description}</Label>
        </div>
      )}

      {hasDomain ? (
        <>
          <div className="space-y-4">
            <div className="flex flex-col space-y-2">
              <label htmlFor={`accessType-${endpoint.name}`} className="text-sm font-medium">
                Access Type
              </label>
              <Select
                value={accessType}
                onValueChange={(value) => onChange('access_type', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select access type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="subdomain">Subdomain</SelectItem>
                  <SelectItem value="domain_path">Domain Path</SelectItem>
                  <SelectItem value="cluster_ip_path">Cluster IP</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {accessType === AccessEndpointType.SUBDOMAIN && (
              <div className="space-y-4">
                <div className="flex flex-col space-y-2">
                  <label htmlFor={`subdomain-${endpoint.name}`} className="text-sm font-medium">
                    Subdomain
                  </label>
                  <div className="flex items-center space-x-2">
                    <Input
                      id={`subdomain-${endpoint.name}`}
                      value={inputValue}
                      onChange={(e) => {
                        console.log(`Subdomain input changed to: ${e.target.value}`);
                        // For subdomain, store value without any slashes or domain
                        onChange('value', e.target.value);
                      }}
                      placeholder="app"
                      className="flex-1"
                    />
                    <span className="text-sm text-muted-foreground whitespace-nowrap">
                      .{cluster.domainName}
                    </span>
                  </div>
                </div>
                <Alert variant="warning" className="mt-4">
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    You will need to create a DNS record for {inputValue || "your-subdomain"}.{cluster.domainName} pointing to the cluster IP {cluster.access_ip} once the application is deployed.
                  </AlertDescription>
                </Alert>
              </div>
            )}

            {(accessType === AccessEndpointType.DOMAIN_PATH || accessType === AccessEndpointType.CLUSTER_IP_PATH) && (
              <div className="flex flex-col space-y-2">
                <label htmlFor={`path-${endpoint.name}`} className="text-sm font-medium">
                  Path
                </label>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-muted-foreground">
                    {accessType === AccessEndpointType.DOMAIN_PATH ? cluster.domainName : cluster.access_ip}/
                  </span>
                  <Input
                    id={`path-${endpoint.name}`}
                    value={inputValue}
                    onChange={(e) => {
                      // For paths, ensure they start with / when stored
                      const newValue = e.target.value.startsWith('/') ? e.target.value : '/' + e.target.value;
                      console.log(`Path input changed to: ${newValue}`);
                      onChange('value', newValue);
                    }}
                    placeholder="app"
                    className="flex-1"
                  />
                </div>
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="flex flex-col space-y-2">
          <label htmlFor={`path-${endpoint.name}`} className="text-sm font-medium">
            Path
          </label>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-muted-foreground">{cluster.access_ip}/</span>
            <Input
              id={`path-${endpoint.name}`}
              value={inputValue}
              onChange={(e) => {
                // For paths, ensure they start with / when stored
                const newValue = e.target.value.startsWith('/') ? e.target.value : '/' + e.target.value;
                console.log(`Path input changed to: ${newValue}`);
                onChange('value', newValue);
              }}
              placeholder="app"
              className="flex-1"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default AccessConfigStep;
