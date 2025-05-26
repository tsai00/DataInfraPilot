from typing import override, Any

from src.core.apps.actions.base_post_install_action import BasePostInstallAction
from src.core.kubernetes.kubernetes_cluster import KubernetesCluster
from src.core.template_loader import template_loader


class ApplyTemplatePostInstallAction(BasePostInstallAction):
    def __init__(self, name: str, template_name: str, template_module: str | None, with_custom_objects: bool = False):
        self.template_name = template_name
        self.template_module = template_module
        self.with_custom_objects = with_custom_objects

        super().__init__(name=name)

    @override
    def run(self, cluster: KubernetesCluster, namespace: str, config_values: dict[str, Any]):
        values = {namespace: namespace, **config_values}

        with template_loader.render_to_temp_file(self.template_name, values, self.template_module) as rendered_template_file:
            cluster.apply_file(rendered_template_file, with_custom_objects=self.with_custom_objects)

    def _validate(self):
        if not self.template_name.endswith('.yaml'):
            raise ValueError(f"Template file {self.template_name} must be a YAML file.")
