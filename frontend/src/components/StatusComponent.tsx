
import React from "react";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";
import { stateEnum } from "@/types/stateEnum";
import { Info } from "lucide-react";

export interface ClusterStatusProps {
  status: stateEnum;
  errorMessage?: string;
}

const statusColorMap: Record<stateEnum, string> = {
  [stateEnum.RUNNING]: "bg-green-500 animate-pulse-light",
  [stateEnum.FAILED]: "bg-red-500",
  [stateEnum.DELETING]: "bg-red-400 animate-pulse-light",
  [stateEnum.CREATING]: "bg-amber-500 animate-pulse-light",
  [stateEnum.UPDATING]: "bg-amber-500 animate-pulse-light",
  [stateEnum.DEPLOYING]: "bg-amber-500 animate-pulse-light",
};

export const StatusComponent: React.FC<ClusterStatusProps> = ({
  status,
  errorMessage,
}) => {
    return (
      <div className="flex items-center">
        <TooltipProvider>
          {status === stateEnum.FAILED && errorMessage ? (
            <Tooltip delayDuration={200}>
              <TooltipTrigger asChild>
                <div className="flex items-center cursor-pointer group">
                  <div className="w-2 h-2 rounded-full mr-2 bg-red-500"></div>
                  <span className="capitalize mr-2">{status}</span>
                  <Info className="text-red-500 h-5 w-5 ml-1 group-hover:scale-110 transition-transform" />
                </div>
              </TooltipTrigger>
              <TooltipContent side="top">
                <span className="text-red-500 font-medium flex items-center mb-1">
                  Error
                </span>
                <span className="whitespace-pre-line">{errorMessage}</span>
              </TooltipContent>
            </Tooltip>
          ) : (
            <div className="flex items-center">
              <div
                className={`w-2 h-2 rounded-full mr-2 ${statusColorMap[status] ?? "bg-muted-foreground animate-pulse-light"}`}
              ></div>
              <span className="capitalize">{status}</span>
            </div>
          )}
        </TooltipProvider>
      </div>
    );
  
};

export default StatusComponent;
