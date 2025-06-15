from datetime import datetime

from pydantic import BaseModel, Field

from src.api.schemas.deployment import DeploymentSchema


class TraefikDashboardConfig(BaseModel):
    enabled: bool = Field(default=True)
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=4, max_length=20)


class ClusterAdditionalComponents(BaseModel):
    traefik_dashboard: TraefikDashboardConfig

    def to_dict(self) -> dict:
        return {
            'traefik_dashboard': self.traefik_dashboard.model_dump(),
        }


class NodePoolAutoscalingConfig(BaseModel):
    enabled: bool = Field(default=False)
    min_nodes: int = Field(default=1, ge=0, le=9)
    max_nodes: int = Field(default=5, ge=1, le=10)

    @property
    def is_valid(self) -> bool:
        return self.max_nodes >= self.min_nodes if self.enabled else True

    def to_dict(self) -> dict:
        return {'enabled': self.enabled, 'min_nodes': self.min_nodes, 'max_nodes': self.max_nodes}


class ClusterPool(BaseModel):
    name: str
    node_type: str
    region: str
    number_of_nodes: int
    autoscaling: NodePoolAutoscalingConfig | None = Field(default=None)

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'node_type': self.node_type,
            'region': self.region,
            'number_of_nodes': self.number_of_nodes,
            'autoscaling': self.autoscaling.to_dict() if self.autoscaling else None,
        }


class ClusterCreateSchema(BaseModel):
    name: str
    k3s_version: str
    provider: str
    provider_config: dict
    domain_name: str | None
    pools: list[ClusterPool]
    additional_components: ClusterAdditionalComponents


class ClusterSchema(ClusterCreateSchema):
    id: int
    status: str
    error_message: str
    access_ip: str
    created_at: datetime
    deployments: list[DeploymentSchema] = Field(default=[])

    class Config:
        from_attributes = True


class ClusterCreateResponseSchema(BaseModel):
    name: str
    status: str
