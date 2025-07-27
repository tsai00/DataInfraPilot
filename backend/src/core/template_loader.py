import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template, meta
from jinja2.exceptions import TemplateNotFound
from src.core.utils import setup_logger


class TemplateLoader:
    _TEMPLATE_SUBFOLDERS = ('kubernetes', 'traefik')

    def __init__(self, templates_dir: Path | None = None) -> None:
        self._logger = setup_logger('TemplateLoader')

        if templates_dir is None:
            templates_dir = Path(__file__).parent.resolve() / 'templates'

        if not templates_dir.is_dir() or not templates_dir.exists():
            raise FileNotFoundError(
                f'Templates directory not found at: {templates_dir}. '
                "Please ensure a 'templates' folder exists next to your script."
            )

        self._environment = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)

    def _validate_template_module(self, template_module: str | None) -> str:
        if template_module is not None and template_module not in self._TEMPLATE_SUBFOLDERS:
            raise ValueError(
                f"Invalid template module: '{template_module}'. Must be one of {self._TEMPLATE_SUBFOLDERS} or None."
            )

        return './' if template_module is None else template_module

    def _search_template(self, template_full_path: str) -> Template:
        try:
            return self._environment.get_template(template_full_path)
        except TemplateNotFound as e:
            self._logger.exception(f"Template '{template_full_path}' not found.", exc_info=False)
            raise TemplateNotFound(
                f"Template '{template_full_path}' not found. "
                "Please ensure the template file exists in the correct path relative to the 'templates' directory."
            ) from e

    def get_template(self, template_name: str, template_module: str | None = None) -> Path:
        resolved_template_module = self._validate_template_module(template_module)

        template_full_path = f'{resolved_template_module}/{template_name}'

        return Path(self._search_template(template_full_path).filename)

    def render_template(
        self, template_name: str, template_module: str | None = None, values: dict[str, Any] | None = None
    ) -> str:
        values = values or {}

        if not isinstance(values, dict):
            msg = 'Template values must be a dictionary'
            self._logger.exception(msg, exc_info=True)
            raise TypeError(msg)

        resolved_template_module = self._validate_template_module(template_module)

        template_full_path = f'{resolved_template_module}/{template_name}'

        template = self._search_template(template_full_path)

        if values:
            template_source = self._environment.loader.get_source(self._environment, template_full_path)[0]
            parsed_ast = self._environment.parse(template_source)
            template_variables = meta.find_undeclared_variables(parsed_ast)

            undeclared_variables = template_variables - values.keys()

            if undeclared_variables:
                raise ValueError(
                    f"There are variables in the template '{template_full_path}' "
                    f"that are not provided in the 'values' dictionary: {undeclared_variables}"
                )

        return template.render(**values)

    @contextmanager
    def render_to_temp_file(
        self, template_name: str, values: dict[str, Any], template_module: str | None = None
    ) -> Generator[Path, None, None]:
        rendered_content = self.render_template(template_name, template_module, values)

        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', delete=False, suffix='.tmp', prefix='rendered_template_', encoding='utf-8'
            ) as temp_file_object:
                temp_file_path = temp_file_object.name

                temp_file_object.write(rendered_content)

            yield Path(temp_file_object.name)

        finally:
            if temp_file_path:
                Path(temp_file_path).unlink(missing_ok=True)


template_loader = TemplateLoader()
