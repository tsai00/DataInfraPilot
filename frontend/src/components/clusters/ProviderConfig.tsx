import React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Provider } from "@/types";

interface ProviderConfigProps {
  provider: Provider;
  providerApiToken: string;
  onProviderApiTokenChange: (token: string) => void;
  sshPrivateKeyPath?: string;
  onSshPrivateKeyPathChange?: (path: string) => void;
  sshPublicKeyPath?: string;
  onSshPublicKeyPathChange?: (path: string) => void;
}

const ProviderConfig: React.FC<ProviderConfigProps> = ({
  provider,
  providerApiToken,
  onProviderApiTokenChange,
  sshPrivateKeyPath,
  onSshPrivateKeyPathChange,
  sshPublicKeyPath,
  onSshPublicKeyPathChange,
}) => {
  const handlePrivateKeyPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newPrivateKeyPath = e.target.value;
    if (onSshPrivateKeyPathChange) {
      onSshPrivateKeyPathChange(newPrivateKeyPath);
    }

    // Automatically update the public key path to match the private key path with .pub suffix
    if (onSshPublicKeyPathChange && !newPrivateKeyPath.endsWith('.pub')) {
      onSshPublicKeyPathChange(`${newPrivateKeyPath}.pub`);
    }
  };

  const renderHetznerConfig = () => (
    <>
      <div className="border rounded-lg p-4 space-y-4 mt-4">
        <h3 className="font-medium">Hetzner Cloud Configuration</h3>
        <div>
          <Label htmlFor="hetzner-token" className="mb-2 block">
            Hetzner Cloud API Token
          </Label>
          <Input
            id="provider-api-token"
            value={providerApiToken}
            onChange={(e) => onProviderApiTokenChange(e.target.value)}
            type="password"
            placeholder="Enter your Hetzner Cloud API token"
            className="mb-1"
          />
          <p className="text-xs text-muted-foreground">
            The API token used to create resources in your Hetzner Cloud account
          </p>
        </div>
      </div>

      <div className="border rounded-lg p-4 space-y-4 mt-4">
        <h3 className="font-medium">SSH Key Configuration</h3>
        <div>
          <Label htmlFor="ssh-private-key" className="mb-2 block">
            SSH Private Key Path
          </Label>
          <Input
            id="ssh-private-key"
            value={sshPrivateKeyPath || ""}
            onChange={handlePrivateKeyPathChange}
            placeholder="~/.ssh/id_rsa"
            className="mb-1"
          />
          <p className="text-xs text-muted-foreground">
            Path to your SSH private key file on your local machine
          </p>
        </div>

        <div>
          <Label htmlFor="ssh-public-key" className="mb-2 block">
            SSH Public Key Path
          </Label>
          <Input
            id="ssh-public-key"
            value={sshPublicKeyPath || ""}
            onChange={(e) => onSshPublicKeyPathChange?.(e.target.value)}
            placeholder="~/.ssh/id_rsa.pub"
            className="mb-1"
          />
          <p className="text-xs text-muted-foreground">
            Path to your SSH public key file on your local machine
          </p>
        </div>
      </div>
    </>
  );

  const renderDigitalOceanConfig = () => (
    <div className="border rounded-lg p-4 space-y-4 mt-4">
      <h3 className="font-medium">DigitalOcean Configuration</h3>
      <div>
        <Label htmlFor="do-token" className="mb-2 block">
          DigitalOcean API Token
        </Label>
        <Input
          id="provider-api-token"
          value={providerApiToken}
          onChange={(e) => onProviderApiTokenChange(e.target.value)}
          type="password"
          placeholder="Enter your DigitalOcean API token"
          className="mb-1"
        />
        <p className="text-xs text-muted-foreground">
          Personal access token from your DigitalOcean account (API section)
        </p>
      </div>
    </div>
  );

  switch (provider.id) {
    case "hetzner":
      return renderHetznerConfig();
    case "digitalocean":
      return renderDigitalOceanConfig();
    default:
      return null;
  }
};

export default ProviderConfig;