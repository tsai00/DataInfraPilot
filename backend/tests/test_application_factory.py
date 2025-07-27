import pytest

from functools import lru_cache
from typing import Any
from pydantic import BaseModel

from src.core.apps.application_factory import ApplicationFactory, ApplicationMetadata
from src.core.apps.base_application import BaseApplication
from src.core.kubernetes.chart_config import HelmChart


class TestApplicationConfig(BaseModel):
    port: int = 8080
    replica_count: int = 1
    custom_message: str = "Test"


class TestApplication(BaseApplication):
    _helm_chart = HelmChart(
        name='test-app',
        repo_url='https://example.com/charts',
        version='1.0.0',
    )

    credentials_secret_name = 'test-app-creds'

    def __init__(self, config: TestApplicationConfig) -> None:
        self._config = config
        super().__init__('TestApp')

    @classmethod
    @lru_cache
    def get_available_versions(cls) -> list[str]: return []

    @classmethod
    def get_volume_requirements(cls): return []

    @classmethod
    def get_accessible_endpoints(cls): return []

    @classmethod
    def get_resource_values(cls) -> dict: return {}

    def _generate_endpoint_helm_values(
        self, endpoint_config, cluster_base_ip: str, namespace: str
    ) -> dict[str, Any]:
        return {}

    def get_ingress_helm_values(
        self, access_endpoint_configs, cluster_base_ip: str, namespace: str
    ) -> dict[str, Any]:
        return {}

    @property
    def chart_values(self) -> dict[str, Any]: return {}


@pytest.fixture(autouse=True)
def clean_registry():
    ApplicationFactory._registry.clear()
    yield


class TestApplicationFactory:
    def test_register_application_success(self):
        app_id = 1
        app_class = TestApplication
        config_class = TestApplicationConfig
        metadata = ApplicationMetadata(username_key='web_user', password_key='web_pass')

        ApplicationFactory.register_application(app_id, app_class, config_class, metadata)

        assert app_id in ApplicationFactory._registry
        registered_app_class, registered_config_class, registered_metadata = ApplicationFactory._registry[app_id]
        assert registered_app_class is app_class
        assert registered_config_class is config_class
        assert registered_metadata == metadata

    def test_register_application_with_default_metadata(self):
        app_id = 2
        app_class = TestApplication
        config_class = TestApplicationConfig

        ApplicationFactory.register_application(app_id, app_class, config_class)

        assert app_id in ApplicationFactory._registry
        registered_app_class, registered_config_class, registered_metadata = ApplicationFactory._registry[app_id]
        assert registered_app_class is app_class
        assert registered_config_class is config_class
        assert registered_metadata == ApplicationMetadata()

    def test_register_application_already_registered(self):
        app_id = 3
        ApplicationFactory.register_application(app_id, TestApplication, TestApplicationConfig)

        with pytest.raises(ValueError, match=f"Application ID '{app_id}' is already registered."):
            ApplicationFactory.register_application(app_id, TestApplication, TestApplicationConfig)

    def test_get_app_info_success(self):
        app_id = 4
        app_class = TestApplication
        config_class = TestApplicationConfig
        metadata = ApplicationMetadata()
        ApplicationFactory.register_application(app_id, app_class, config_class, metadata)

        retrieved_app_class, retrieved_config_class, retrieved_metadata = ApplicationFactory._get_app_info(app_id)
        assert retrieved_app_class is app_class
        assert retrieved_config_class is config_class
        assert retrieved_metadata is metadata

    def test_get_app_info_not_registered(self):
        app_id = 99
        with pytest.raises(ValueError, match=f"Application with ID '{app_id}' is not registered."):
            ApplicationFactory._get_app_info(app_id)

    def test_get_application_class_success(self):
        app_id = 5
        ApplicationFactory.register_application(app_id, TestApplication, TestApplicationConfig)
        assert ApplicationFactory.get_application_class(app_id) is TestApplication

    def test_get_application_class_not_registered(self):
        app_id = 100
        with pytest.raises(ValueError, match=f"Application with ID '{app_id}' is not registered."):
            ApplicationFactory.get_application_class(app_id)

    def test_get_application_metadata_success(self):
        app_id = 6
        custom_metadata = ApplicationMetadata(username_key='admin', password_key='secret')
        ApplicationFactory.register_application(app_id, TestApplication, TestApplicationConfig, custom_metadata)
        assert ApplicationFactory.get_application_metadata(app_id) == custom_metadata

    def test_get_application_metadata_default(self):
        app_id = 7
        ApplicationFactory.register_application(app_id, TestApplication, TestApplicationConfig)
        assert ApplicationFactory.get_application_metadata(app_id) == ApplicationMetadata()

    def test_get_application_metadata_not_registered(self):
        app_id = 101
        with pytest.raises(ValueError, match=f"Application with ID '{app_id}' is not registered."):
            ApplicationFactory.get_application_metadata(app_id)

    def test_get_application_success(self):
        app_id = 8
        ApplicationFactory.register_application(app_id, TestApplication, TestApplicationConfig)
        config_data = {"port": 9000, "replica_count": 3, "custom_message": "Test Message"}

        app_instance = ApplicationFactory.get_application(app_id, config_data)

        assert isinstance(app_instance, TestApplication)
        assert app_instance._config.port == 9000
        assert app_instance._config.replica_count == 3
        assert app_instance._config.custom_message == "Test Message"

    def test_get_application_not_registered(self):
        app_id = 102
        config_data = {"port": 8080}
        with pytest.raises(ValueError, match=f"Application with ID '{app_id}' is not registered."):
            ApplicationFactory.get_application(app_id, config_data)

    def test_get_registered_app_ids_empty(self):
        assert ApplicationFactory.get_registered_app_ids() == []

    def test_get_registered_app_ids_populated(self):
        ApplicationFactory.register_application(10, TestApplication, TestApplicationConfig)
        ApplicationFactory.register_application(11, TestApplication, TestApplicationConfig)
        ids = ApplicationFactory.get_registered_app_ids()
        assert sorted(ids) == [10, 11]

    def test_get_app_name_by_id_success(self):
        ApplicationFactory.register_application(12, TestApplication, TestApplicationConfig)
        assert ApplicationFactory.get_app_name_by_id(12) == "Test"

    def test_get_app_name_by_id_not_registered(self):
        assert ApplicationFactory.get_app_name_by_id(999) is None