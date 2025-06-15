
import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Cloud, Globe, Home, HardDrive, Settings, ChevronLeft, ChevronRight, Menu, Package } from "lucide-react";
import { useState } from "react";

const sidebarItems = [
  { icon: Home, label: "Dashboard", path: "/" },
  { icon: Cloud, label: "Clusters", path: "/clusters" },
  { icon: Package, label: "Deployments", path: "/deployments" },
  { icon: HardDrive, label: "Volumes", path: "/volumes" },
  // { icon: Globe, label: "Domains", path: "/domains" }
];

const Sidebar: React.FC = () => {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className={`border-r transition-all duration-300 ${collapsed ? "w-16" : "w-64"} relative`}>
      <div className="h-full py-4 px-3 flex flex-col">
        <Button
            variant="ghost"
            size="icon"
            className="mb-4 self-end"
            onClick={() => setCollapsed(!collapsed)}
        >
          <Menu className="h-5 w-5" />
        </Button>
        <div className="flex-1 space-y-1">
          {sidebarItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Button
                key={item.path}
                variant={isActive ? "secondary" : "ghost"}
                className={`w-full ${collapsed ? "justify-center" : "justify-start"} ${
                  isActive ? "bg-k8s-light text-k8s-blue" : ""
                }`}
                asChild
              >
                <Link 
                  to={item.path} 
                  className={`flex items-center gap-3 ${collapsed ? "flex-col" : ""}`}
                >
                  <item.icon className="h-5 w-5" />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              </Button>
            );
          })}
        </div>
        
        {!collapsed && (
          <div className="border-t pt-4 mt-4">
            <div className="text-xs text-muted-foreground px-4 py-2">
              DataInfraPilot v0.1.0
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;
