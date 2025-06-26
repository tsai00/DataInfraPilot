
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
  }
];
