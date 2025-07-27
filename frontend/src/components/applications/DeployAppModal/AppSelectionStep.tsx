
import React, {  } from 'react';
import { Application } from "@/types";
import { Card, CardContent } from '@/components/ui/card';

interface AppSelectionStepProps {
  applications: Application[];
  handleAppSelect: (app: Application) => void;
}

const AppSelectionStep: React.FC<AppSelectionStepProps> = ({
  applications,
  handleAppSelect
}) => {

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 py-4">
      {applications.map((app) => {
        const resources = app.recommendedResources || { nodes: "1", ram: "1 GB", cpu: "1 vCPU" };
        return (
          <Card
            key={app.id}
            className="cursor-pointer hover:border-primary transition-colors"
            onClick={() => handleAppSelect(app)}
          >
            <CardContent className="p-4">
              <div className="flex flex-col items-center text-center gap-3">
                <img
                  src={app.logo}
                  alt={app.name}
                  className="w-16 h-16 object-contain bg-white rounded-lg p-2 mt-2"
                />
                <div>
                  <h3 className="font-medium text-lg">{app.name}</h3>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {app.description}
                  </p>
                  <div className="mt-2 flex items-center justify-center">
                    <div className="mt-2 px-3 py-1 rounded-lg bg-muted/40 border text-xs flex flex-row items-center gap-2 text-muted-foreground">
                      <div className="flex flex-row items-center gap-2">
                        {resources.nodes} nodes • {resources.ram} RAM • {resources.cpu}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};


export default AppSelectionStep;
