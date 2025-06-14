from dataclasses import dataclass
from typing import ClassVar

from pydantic import BaseModel

from src.core.apps.base_application import BaseApplication


@dataclass(frozen=True)
class ApplicationMetadata:
    username_key: str = 'username'
    password_key: str = 'password'  # noqa: S105 (not a secret)


class ApplicationFactory:
    # The internal registry mapping app_id to (AppClass, ConfigClass, ApplicationMetadata).
    _registry: ClassVar[dict[int, tuple[type[BaseApplication], type[BaseModel], ApplicationMetadata]]] = {}

    @classmethod
    def register_application(
        cls,
        app_id: int,
        app_class: type[BaseApplication],
        config_class: type[BaseModel],
        metadata: ApplicationMetadata = None,
    ) -> None:
        if app_id in cls._registry:
            raise ValueError(f"Application ID '{app_id}' is already registered.")

        metadata = metadata or ApplicationMetadata()

        cls._registry[app_id] = (app_class, config_class, metadata)

    @classmethod
    def _get_app_info(cls, app_id: int) -> tuple[type[BaseApplication], type[BaseModel], ApplicationMetadata]:
        info = cls._registry.get(app_id)
        if info is None:
            raise ValueError(f"Application with ID '{app_id}' is not registered.")
        return info

    @classmethod
    def get_application_class(cls, app_id: int) -> type[BaseApplication]:
        app_class, _, _ = cls._get_app_info(app_id)
        return app_class

    @classmethod
    def get_application_metadata(cls, app_id: int) -> ApplicationMetadata:
        _, _, metadata = cls._get_app_info(app_id)
        return metadata

    @staticmethod
    def get_application(application_id: int, application_config: dict) -> BaseApplication:
        app_class, config_class, _ = ApplicationFactory._get_app_info(application_id)

        config_instance = config_class(**application_config)

        return app_class(config_instance)

    @classmethod
    def get_registered_app_ids(cls) -> list[int]:
        return list(cls._registry.keys())

    @classmethod
    def get_app_name_by_id(cls, app_id: int) -> str | None:
        try:
            app_class = cls.get_application_class(app_id)
            return app_class.__name__.replace('Application', '')
        except ValueError:
            return None
