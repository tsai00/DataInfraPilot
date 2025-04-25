from src.core.apps.airflow_application import AirflowApplication, AirflowConfig
from src.core.apps.base_application import BaseApplication
from src.core.apps.grafana_application import GrafanaApplication, GrafanaConfig
from src.core.apps.hashicorp_vault_application import HashicorpVaultApplication, HashicorpVaultConfig


class ApplicationFactory:
    @staticmethod
    def get_application(application_id: int, application_config: dict) -> BaseApplication:
        if application_id == 1:
            return AirflowApplication(AirflowConfig(**application_config))
        elif application_id == 2:
            return GrafanaApplication(GrafanaConfig(**application_config))
        elif application_id == 3:
            return HashicorpVaultApplication(HashicorpVaultConfig(**application_config))
        else:
            raise ValueError(f'Unsupported application with ID {application_id}')