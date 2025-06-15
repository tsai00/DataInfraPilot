
import React from "react";
import { HelpCircle, Settings, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "./ThemeToggle";
import ActivityDropdown from "./ActivityDropdown";
import { Link } from "react-router-dom";

const Navbar: React.FC = () => {
  return (
    <header className="bg-background border-b py-3 px-6 flex items-center justify-between">
      <div className="flex items-center">
        <div className="flex items-center gap-2">
          <div className="bg-k8s-blue rounded-md p-1">
            <img
              src="https://upload.wikimedia.org/wikipedia/commons/3/39/Kubernetes_logo_without_workmark.svg"
              alt="Kubernetes Logo"
              className="h-6 w-6"
            />
          </div>
          <h1 className="text-xl font-semibold">DataInfraPilot</h1>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <ThemeToggle />
        <ActivityDropdown />
        <Button variant="ghost" size="icon">
          <HelpCircle className="h-5 w-5" />
        </Button>
        {/* <Link to="/settings">
          <Button variant="ghost" size="icon">
            <Settings className="h-5 w-5" />
          </Button>
        </Link> */}
        {/* <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full">
              <User className="h-5 w-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Profile</DropdownMenuItem>
            <DropdownMenuItem>API Keys</DropdownMenuItem>
            <DropdownMenuItem>Settings</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Log out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu> */}
      </div>
    </header>
  );
};

export default Navbar;
