
import React from "react";

interface Step {
  id: string;
  label: string;
}

interface StepProgressProps {
  steps: Step[];
  currentStep: number;
}

export function StepProgress({ steps, currentStep }: StepProgressProps) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center space-x-2">
        {steps.map((step, index) => (
          <React.Fragment key={step.id}>
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center ${
                currentStep >= index + 1 ? "bg-k8s-blue text-white" : "bg-muted text-muted-foreground"
              }`}
            >
              {index + 1}
            </div>
            {index < steps.length - 1 && (
              <div className="h-1 w-8 bg-muted">
                <div
                  className={`h-full ${currentStep >= index + 2 ? "bg-k8s-blue" : "bg-muted"}`}
                />
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
