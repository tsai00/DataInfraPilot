
import { Application, ConfigOption } from "@/types";

// Common configuration options for all applications
const commonConfigOptions: ConfigOption[] = [];

export const applications: Application[] = [
    {
      id: 1,
      short_name: "airflow",
      name: "Apache Airflow",
      description: "Platform to programmatically author, schedule and monitor workflows",
      logo: "/airflow-logo.png",
      recommendedResources: {
        nodes: "2",
        ram: "4 GB",
        cpu: "2 vCPU",
      },
      volumeRequirements: [
        {
          id: "1",
          name: "airflow-logs",
          defaultSize: 50,
          description: "Persistent storage for Airflow logs"
        }
      ],
      configOptions: [
        ...commonConfigOptions,
        {
          id: "version",
          name: "Airflow Version",
          type: "select",
          description: "Version of Airflow to deploy",
          required: true,
          default: "2.8.1",
          options: [],
          applicationId: 1
        },
        {
          id: "executor",
          name: "Executor",
          type: "select",
          description: "Determines how Airflow tasks are executed",
          required: true,
          default: "CeleryExecutor",
          options: [
            { value: "CeleryExecutor", label: "CeleryExecutor (Recommended)" },
            { value: "KubernetesExecutor", label: "KubernetesExecutor" },
            { value: "LocalExecutor", label: "LocalExecutor" },
          ],
        },
        {
          id: "instance_name",
          name: "Instance Name",
          type: "text",
          default: "Airflow",
          description: "A unique name for this Airflow instance",
          required: true,
        },
        {
          id: "pgbouncer_enabled",
          name: "PGBouncer Enabled",
          type: "boolean",
          description: "Use PGBouncer for connection pooling to the database",
          required: false,
          default: true,
        },
        {
          id: "flower_enabled",
          name: "Flower Enabled",
          type: "boolean",
          description: "Enable Flower for Celery task monitoring",
          required: false,
          default: true,
        },
        // Add DAG repository configuration fields
        {
          id: "dags_repository",
          name: "DAGs Git Repository URL",
          type: "text",
          description: "Enter the URL of your Git repository containing the Airflow DAGs",
          required: true,
          default: "",
        },
        {
          id: "dags_repository_branch",
          name: "Branch Name",
          type: "text",
          description: "Branch to use for DAGs repository",
          required: true,
          default: "main",
        },
        {
          id: "dags_repository_subpath",
          name: "DAG Folder Name",
          type: "text",
          description: "Folder in your repo with DAGs",
          required: true,
          default: "dags",
        },
        {
          id: "dags_repository_private",
          name: "Repository is private",
          type: "boolean",
          description: "Enable if your repository requires SSH key authentication",
          required: false,
          default: false,
        },
        {
          id: "dags_repository_ssh_private_key",
          name: "SSH Private Key",
          type: "text",
          description: "SSH key for accessing private Git repository (only required if repository is private)",
          required: false,
          default: "",
          conditional: {
            field: "dags_repository_ssh_private_key",
            value: true
          }
        },
      ],
    },
    {
      id: 2,
      short_name: "grafana",
      name: "Grafana",
      description: "Multi-platform open source analytics and interactive visualization web application.",
      logo: "/grafana-logo.png",
      recommendedResources: {
        nodes: "2",
        ram: "2 GB",
        cpu: "1 vCPU",
      },
      configOptions: [
        ...commonConfigOptions,
        {
          id: "version",
          name: "Grafana Version",
          type: "select",
          description: "Version of Grafana to deploy",
          required: true,
          default: "11.6",
          options: [],
          applicationId: 2
        },
        {
          id: "number_of_replicas",
          name: "Number of replicas",
          type: "number",
          description: "Number of Grafana replicas (for higher / lower load)",
          required: true,
          default: 1,
        },
      ],
    },
    {
      id: 3,
      short_name: "spark",
      name: "Apache Spark",
      description: "Tool for running Big Data jobs.",
      logo: "/spark-logo.png",
      recommendedResources: {
        nodes: "2",
        ram: "2 GB",
        cpu: "1 vCPU",
      },
      configOptions: [
        ...commonConfigOptions,
        {
          id: "version",
          name: "Spark Version",
          type: "select",
          description: "Version of Spark to deploy",
          required: true,
          default: "3.5.1",
          options: [],
          applicationId: 4
        },
        {
          id: "cluster_name",
          name: "Cluster Name",
          type: "text",
          default: "SparkProd",
          description: "A unique name for this Spark cluster",
          required: true,
        },
        {
          id: "min_workers",
          name: "Minimum number of worker nodes",
          type: "number",
          description: "Minimum required number of Spark worker nodes",
          required: true,
          default: 1,
        },
        {
          id: "max_workers",
          name: "Maximum number of worker nodes",
          type: "number",
          description: "Maximum required number of Spark worker nodes",
          required: true,
          default: 3,
        },
      ],
    },
    {
      id: 4,
      short_name: "prefect",
      name: "Prefect",
      description: "Orchestration tool",
      logo: "/prefect-logo.svg",
      recommendedResources: {
        nodes: "2",
        ram: "2 GB",
        cpu: "1 vCPU",
      },
      configOptions: [
        ...commonConfigOptions,
        {
          id: "admin_username",
          name: "Admin Username",
          type: "text",
          description: "Default admin username for Grafana",
          required: true,
          default: "admin",
        },
        {
          id: "admin_password",
          name: "Admin Password",
          type: "text",
          description: "Default admin password for Grafana",
          required: true,
          default: "",
        }
      ],
    },
    // {
    //   id: 5,
    //   short_name: "superset",
    //   name: "Superset",
    //   description: "Visualisation.",
    //   logo: "/superset-logo.svg",
    //   recommendedResources: {
    //     nodes: "2",
    //     ram: "2 GB",
    //     cpu: "1 vCPU",
    //   },
    //   configOptions: [
    //     ...commonConfigOptions,
    //   ],
    // },
  ];
