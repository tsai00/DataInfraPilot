
import { Provider } from "@/types";

export const providers: Provider[] = [
  {
    id: "hetzner",
    name: "Hetzner",
    logo: "/hetzner-logo.png",
    description: "High-performance cloud infrastructure at fair prices",
    regions: [
      {
        id: "fsn1",
        name: "Falkenstein",
        location: "Germany",
        flag: "🇩🇪",
      },
      {
        id: "nbg1",
        name: "Nuremberg",
        location: "Germany",
        flag: "🇩🇪",
      },
      {
        id: "hel1",
        name: "Helsinki",
        location: "Finland",
        flag: "🇫🇮",
      },
    ],
    volumeCostGbPerHour: 0.0484,
    nodeTypes: [
      {
        id: "cx22",
        name: "CX22",
        cpu: 2,
        memory: 4,
        description: "2 vCPU, 4 GB RAM",
        hourlyCost: 0.006,    // in EUR
      },
      {
        id: "cx32",
        name: "CX32",
        cpu: 4,
        memory: 8,
        description: "4 vCPU, 8 GB RAM",
        hourlyCost: 0.0113,   // in EUR
      },
      {
        id: "cx42",
        name: "CX42",
        cpu: 8,
        memory: 16,
        description: "8 vCPU, 16 GB RAM",
        hourlyCost: 0.0273,   // in EUR
      },
      {
        id: "cx52",
        name: "CX52",
        cpu: 16,
        memory: 32,
        description: "16 vCPU, 32 GB RAM",
        hourlyCost: 0.054,    // in EUR
      },
    ]
  },
  {
    id: "digitalocean",
    name: "DigitalOcean",
    logo: "/digital-ocean-logo.png",
    description: "Simple cloud computing, built for developers",
    regions: [
      {
        id: "nyc1",
        name: "New York 1",
        location: "United States",
        flag: "🇺🇸",
      },
      {
        id: "sfo3",
        name: "San Francisco 3",
        location: "United States", 
        flag: "🇺🇸",
      },
      {
        id: "ams3",
        name: "Amsterdam 3",
        location: "Netherlands",
        flag: "🇳🇱",
      },
      {
        id: "sgp1",
        name: "Singapore 1",
        location: "Singapore",
        flag: "🇸🇬",
      },
      {
        id: "lon1",
        name: "London 1",
        location: "United Kingdom",
        flag: "🇬🇧",
      },
      {
        id: "fra1",
        name: "Frankfurt 1",
        location: "Germany",
        flag: "🇩🇪",
      },
    ],
    volumeCostGbPerHour: 0.010, // $0.10 per GB per month / (30 * 24)
    nodeTypes: [
      {
        id: "s-2vcpu-2gb",
        name: "Basic 2GB",
        cpu: 2,
        memory: 2,
        description: "2 vCPU, 2 GB RAM",
        hourlyCost: 0.018, // $0.018/hr
      },
      {
        id: "s-2vcpu-4gb",
        name: "Basic 4GB",
        cpu: 2,
        memory: 4,
        description: "2 vCPU, 4 GB RAM",
        hourlyCost: 0.036, // $0.036/hr
      },
      {
        id: "s-4vcpu-8gb",
        name: "Basic 8GB",
        cpu: 4,
        memory: 8,
        description: "4 vCPU, 8 GB RAM",
        hourlyCost: 0.071, // $0.071/hr
      },
      {
        id: "s-8vcpu-16gb",
        name: "Basic 16GB",
        cpu: 8,
        memory: 16,
        description: "8 vCPU, 16 GB RAM",
        hourlyCost: 0.143, // $0.143/hr
      },
    ]
  }
];
