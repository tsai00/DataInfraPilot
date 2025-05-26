from pathlib import Path
from typing import override, Any

from jinja2 import Environment, FileSystemLoader

from src.core.apps.actions.base_post_install_action import BasePostInstallAction
from src.core.kubernetes.kubernetes_cluster import KubernetesCluster


class ApplyTemplatePostInstallAction(BasePostInstallAction):
    def __init__(self, name: str, template_path: Path, with_custom_objects: bool = False):
        self.template_path = template_path
        self.with_custom_objects = with_custom_objects

        super().__init__(name=name)

    @override
    def run(self, cluster: KubernetesCluster, namespace: str, config_values: dict[str, Any]):
        environment = Environment(loader=FileSystemLoader(self.template_path.parent))
        template = environment.get_template(self.template_path.name)
        rendered_template = template.render(namespace=namespace, **config_values)

        temp_file = Path(f"/tmp/post_install_action_{self.name}.yaml")
        temp_file.write_text(rendered_template)

        try:
            cluster.apply_file(temp_file, with_custom_objects=self.with_custom_objects)
        except Exception as e:
            print(f"Error applying Helm template: {e}")
        finally:
            temp_file.unlink()

    def _validate(self):
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template file {self.template_path} does not exist.")
        if not self.template_path.is_file():
            raise ValueError(f"Template path {self.template_path} is not a file.")
        if not self.template_path.suffix == '.yaml':
            raise ValueError(f"Template file {self.template_path} must be a YAML file.")
