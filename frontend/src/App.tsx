
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Routes, Route } from "react-router-dom";
import MainLayout from "./components/layout/MainLayout";
import Dashboard from "./pages/Dashboard";
import Clusters from "./pages/Clusters";
import ClusterDetail from "./pages/ClusterDetails";
import DeploymentDetails from "./pages/DeploymentDetails";
import Deployments from "./pages/Deployments";
import Volumes from "./pages/Volumes";
import Domains from "./pages/Domains";
import NotFound from "./pages/NotFound";
import { ThemeProvider } from "./components/layout/ThemeProvider";

const queryClient = new QueryClient();

const App = () => (
  <ThemeProvider defaultTheme="dark">
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <Routes>
          <Route path="/" element={<MainLayout><Dashboard /></MainLayout>} />
          <Route path="/clusters" element={<MainLayout><Clusters /></MainLayout>} />
          <Route path="/clusters/:id" element={<MainLayout><ClusterDetail /></MainLayout>} />
          <Route path="/clusters/:clusterId/deployments/:appId" element={<MainLayout><DeploymentDetails /></MainLayout>} />
          <Route path="/deployments" element={<MainLayout><Deployments /></MainLayout>} />
          <Route path="/volumes" element={<MainLayout><Volumes /></MainLayout>} />
          {/* <Route path="/domains" element={<MainLayout><Domains /></MainLayout>} /> */}
          <Route path="/settings" element={<MainLayout><Dashboard /></MainLayout>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </TooltipProvider>
    </QueryClientProvider>
  </ThemeProvider>
);

export default App;
