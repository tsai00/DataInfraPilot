
import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Globe, Plus, Trash, ExternalLink, Check, X } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useClusterStore } from "@/store";
import { useToast } from "@/hooks/use-toast";

const Domains: React.FC = () => {
  const { domains, addDomain, deleteDomain } = useClusterStore();
  const { toast } = useToast();
  const [newDomain, setNewDomain] = useState("");
  const [deletingDomain, setDeletingDomain] = useState<string | null>(null);

  const handleAddDomain = () => {
    if (!newDomain) return;
    
    addDomain(newDomain);
    toast({
      title: "Domain added",
      description: `${newDomain} has been added and is pending verification.`,
    });
    setNewDomain("");
  };

  const handleDeleteDomain = (domainId: string) => {
    setDeletingDomain(domainId);
  };

  const confirmDeleteDomain = () => {
    if (deletingDomain) {
      const domainName = domains.find(d => d.id === deletingDomain)?.name || "";
      deleteDomain(deletingDomain);
      toast({
        title: "Domain deleted",
        description: `${domainName} has been removed.`,
      });
      setDeletingDomain(null);
    }
  };

  const cancelDeleteDomain = () => {
    setDeletingDomain(null);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Domains</h1>
          <p className="text-muted-foreground">
            Manage custom domains for your clusters and applications
          </p>
        </div>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Add Domain</CardTitle>
          <CardDescription>
            Add a custom domain to use with your clusters and applications
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="Enter domain (e.g., app.example.com)"
              value={newDomain}
              onChange={(e) => setNewDomain(e.target.value)}
              className="flex-1"
            />
            <Button onClick={handleAddDomain}>
              <Plus className="mr-2 h-4 w-4" />
              Add Domain
            </Button>
          </div>
        </CardContent>
      </Card>

      <h2 className="text-xl font-semibold mb-4">Your Domains</h2>
      
      {domains.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center p-6">
            <Globe className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No domains added yet</h3>
            <p className="text-muted-foreground text-center mb-4">
              Add your first domain to start using it with your applications
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {domains.map((domain) => (
            <Card key={domain.id} className="border hover:border-primary hover:shadow-sm transition-all">
              <CardContent className="p-4 flex justify-between items-center">
                <div className="flex items-center">
                  <Globe className="h-5 w-5 mr-3 text-muted-foreground" />
                  <div>
                    <p className="font-medium">{domain.name}</p>
                    <div className="flex items-center gap-1">
                      {domain.status === "verified" ? (
                        <>
                          <Check className="h-3 w-3 text-green-500" />
                          <span className="text-xs text-green-500">Verified</span>
                        </>
                      ) : (
                        <>
                          <X className="h-3 w-3 text-amber-500" />
                          <span className="text-xs text-amber-500">Pending verification</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="icon">
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    onClick={() => handleDeleteDomain(domain.id)}
                  >
                    <Trash className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <AlertDialog open={!!deletingDomain} onOpenChange={(open) => !open && setDeletingDomain(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action will remove the domain from your account. Any applications using this domain will no longer be accessible through it.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={cancelDeleteDomain}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDeleteDomain} className="bg-destructive text-destructive-foreground">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Domains;
