
import React, { useEffect, useState } from "react";
import { AlertTriangle, Key, Copy, Check } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { getDeploymentCredentials } from "@/services/api";
import { useToast } from "@/hooks/use-toast";

interface CredentialsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  clusterId: string;
  deploymentId: string;
  applicationName: string;
}

interface Credentials {
  username: string;
  password: string;
}

const CredentialsModal: React.FC<CredentialsModalProps> = ({
  open,
  onOpenChange,
  clusterId,
  deploymentId,
  applicationName,
}) => {
  const [credentials, setCredentials] = useState<Credentials | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    const fetchCredentials = async () => {
      if (!open) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const data = await getDeploymentCredentials(clusterId, deploymentId);
        setCredentials(data);
      } catch (err) {
        console.error("Failed to fetch credentials:", err);
        setError(err instanceof Error ? err.message : "Failed to fetch credentials");
        toast({
          title: "Error",
          description: "Could not retrieve application credentials",
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchCredentials();
  }, [open, clusterId, deploymentId, toast]);

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text).then(
      () => {
        setCopiedField(field);
        toast({
          title: "Copied!",
          description: `${field} copied to clipboard`,
        });
        
        // Reset copied status after 2 seconds
        setTimeout(() => {
          setCopiedField(null);
        }, 2000);
      },
      (err) => {
        console.error("Failed to copy text: ", err);
        toast({
          title: "Error",
          description: "Failed to copy to clipboard",
          variant: "destructive",
        });
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            {applicationName} Credentials
          </DialogTitle>
          <DialogDescription>
            Use these credentials to access your application for the first time.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <Alert variant="warning" className="bg-amber-50 dark:bg-amber-950/30">
            <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            <AlertDescription className="text-amber-800 dark:text-amber-400">
              For security reasons, please change these default credentials after your first login.
            </AlertDescription>
          </Alert>

          {loading && <div className="text-center py-4">Loading credentials...</div>}

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {credentials && !loading && (
            <div className="space-y-3 border rounded-md p-3">
              <div>
                <div className="text-sm font-medium text-muted-foreground">Username</div>
                <div className="font-mono bg-muted p-2 rounded-sm mt-1 text-sm flex justify-between items-center">
                  <span>{credentials.username}</span>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-8 px-2"
                    onClick={() => copyToClipboard(credentials.username, "Username")}
                  >
                    {copiedField === "Username" ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
              <div>
                <div className="text-sm font-medium text-muted-foreground">Password</div>
                <div className="font-mono bg-muted p-2 rounded-sm mt-1 text-sm flex justify-between items-center">
                  <span>{credentials.password}</span>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-8 px-2"
                    onClick={() => copyToClipboard(credentials.password, "Password")}
                  >
                    {copiedField === "Password" ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default CredentialsModal;
