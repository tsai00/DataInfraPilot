import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from src.core.template_loader import TemplateLoader
from jinja2.exceptions import TemplateNotFound


@pytest.fixture
def temp_templates_dir_root():
    """
    Creates a temporary directory that will serve as the 'templates' root for tests.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        templates_root = Path(tmpdir)

        # Create subfolders
        (templates_root / 'kubernetes').mkdir()
        (templates_root / 'traefik').mkdir()

        # Create dummy template files
        (templates_root / 'kubernetes' / 'deployment.yaml').write_text(
            'apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {{ app_name }}'
        )
        (templates_root / 'traefik' / 'ingress.yaml').write_text(
            'apiVersion: traefik.io/v1alpha1\nkind: IngressRoute\nmetadata:\n  name: {{ service_name }}-ingress'
        )
        (templates_root / 'simple.txt').write_text('Hello, {{ name }}!')
        (templates_root / 'no_vars.txt').write_text('This is a test.')

        yield templates_root


@pytest.fixture
def template_loader(temp_templates_dir_root):
    return TemplateLoader(templates_dir=temp_templates_dir_root)


@pytest.fixture(autouse=True)
def mock_setup_logger():
    with patch('src.core.utils.setup_logger') as mock_logger:
        mock_logger.return_value = MagicMock()
        yield


class TestTemplateLoader:
    def test_init_templates_dir_not_found(self):
        non_existent_path = Path("/path/to/nonexistent/templates_xyz")
        if non_existent_path.exists():
            non_existent_path.rmdir()

        with pytest.raises(FileNotFoundError, match=f"Templates directory not found at: {non_existent_path}."):
            TemplateLoader(templates_dir=non_existent_path)

    @pytest.mark.parametrize(
        "module, expected",
        [
            ("kubernetes", "kubernetes"),
            ("traefik", "traefik"),
        ],
    )
    def test_validate_template_module_valid(self, template_loader, temp_templates_dir_root, module, expected):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        assert template_loader._validate_template_module(module) == expected

    def test_validate_template_module_none(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        assert template_loader._validate_template_module(None) == "./"

    def test_validate_template_module_invalid(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        with pytest.raises(
            ValueError,
            match=r"Invalid template module: 'invalid'. Must be one of \('kubernetes', 'traefik'\) or None.",
        ):
            template_loader._validate_template_module("invalid")

    def test_get_template_success_with_module(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        template_path = template_loader.get_template("deployment.yaml", "kubernetes")
        assert template_path == temp_templates_dir_root / 'kubernetes' / 'deployment.yaml'
        assert template_path.is_file()

    def test_get_template_success_no_module(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        template_path = template_loader.get_template("simple.txt")
        assert template_path == temp_templates_dir_root / 'simple.txt'
        assert template_path.is_file()

    def test_get_template_not_found(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        with pytest.raises(
            TemplateNotFound,
            match="Template 'kubernetes/non_existent.yaml' not found.",
        ):
            template_loader.get_template("non_existent.yaml", "kubernetes")

    def test_get_template_invalid_module(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        with pytest.raises(ValueError):
            template_loader.get_template("simple.txt", "invalid")

    def test_render_template_no_variables(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        rendered_content = template_loader.render_template("no_vars.txt")
        assert rendered_content == "This is a test."

    def test_render_template_with_variables(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        values = {"name": "World"}
        rendered_content = template_loader.render_template("simple.txt", values=values)
        assert rendered_content == "Hello, World!"

    def test_render_template_with_module_and_variables(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        values = {"app_name": "my-app"}
        rendered_content = template_loader.render_template(
            "deployment.yaml", template_module="kubernetes", values=values
        )
        assert "name: my-app" in rendered_content
        assert "apiVersion: apps/v1" in rendered_content

    def test_render_template_missing_variables(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        values = {"another_var": "something"}
        with pytest.raises(
            ValueError,
            match="There are variables in the template './/simple.txt' that are not provided in the 'values' dictionary: {'name'}",
        ):
            template_loader.render_template("simple.txt", values=values)

    def test_render_template_not_found(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        with pytest.raises(
            TemplateNotFound,
            match="Template 'kubernetes/non_existent.yaml' not found.",
        ):
            template_loader.render_template("non_existent.yaml", "kubernetes")

    def test_render_template_invalid_module(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        with pytest.raises(ValueError):
            template_loader.render_template("simple.txt", "invalid")

    def test_render_template_values_not_dict(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        with pytest.raises(TypeError, match="Template values must be a dictionary"):
            template_loader.render_template("simple.txt", values="not_a_dict")

    def test_render_to_temp_file_success(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        values = {"name": "Test"}
        temp_file_path = None
        with template_loader.render_to_temp_file("simple.txt", values=values) as f_path:
            temp_file_path = f_path
            assert temp_file_path.is_file()
            assert temp_file_path.name.startswith("rendered_template_")
            assert temp_file_path.suffix == ".tmp"
            assert temp_file_path.read_text() == "Hello, Test!"

        assert not temp_file_path.exists()

    def test_render_to_temp_file_content(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        values = {"app_name": "another-app"}
        with template_loader.render_to_temp_file(
            "deployment.yaml", values=values, template_module="kubernetes"
        ) as f_path:
            content = f_path.read_text()
            assert "name: another-app" in content

    def test_render_to_temp_file_template_not_found(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        values = {"name": "Test"}
        with pytest.raises(TemplateNotFound):
            with template_loader.render_to_temp_file("non_existent.txt", values=values):
                pass

    def test_render_to_temp_file_missing_variables(self, template_loader, temp_templates_dir_root):
        template_loader = TemplateLoader(templates_dir=temp_templates_dir_root)
        values = {"wrong_var": "value"}
        with pytest.raises(ValueError, match="There are variables in the template './/simple.txt' that are not provided in the 'values' dictionary: {'name'}"):
            with template_loader.render_to_temp_file("simple.txt", values=values):
                pass