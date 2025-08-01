from typing import Any, override

from src.core.apps.actions.base_post_install_action import BasePrePostInstallAction
from src.core.kubernetes.kubernetes_cluster import KubernetesCluster
from src.core.template_loader import template_loader


class ApplyTemplateAction(BasePrePostInstallAction):
    def __init__(
        self,
        name: str,
        template_name: str,
        template_module: str | None,
        values: dict | None = None,
        with_custom_objects: bool = False,
        condition: bool = True,
    ) -> None:
        self.template_name = template_name
        self.template_module = template_module
        self.with_custom_objects = with_custom_objects
        self.values = values or {}

        super().__init__(name=name, condition=condition)

    @override
    async def run(self, cluster: KubernetesCluster, namespace: str, config_values: dict[str, Any]) -> None:
        values = {'namespace': namespace, **config_values, **self.values}

        print(f'Applying action with values: {values}')

        with template_loader.render_to_temp_file(
            self.template_name, values, self.template_module
        ) as rendered_template_file:
            cluster.apply_file(rendered_template_file, with_custom_objects=self.with_custom_objects)

    def _validate(self) -> None:
        if not self.template_name.endswith('.yaml'):
            raise ValueError(f'Template file {self.template_name} must be a YAML file.')
