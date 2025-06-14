import argparse
import importlib
import inspect
from datetime import datetime
from functools import partial
from typing import Any, Literal

from src.demo.scrapers.base_scraper import BaseScraper
from src.demo.scrapers.base_transformation import BaseTransformation
from src.demo.utils import setup_logger

logger = setup_logger('OrchestrationUtils')


def parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    projects = ['sreality', 'bezrealitky']

    parser.add_argument('-p', '--project', type=str, help=f'Project (from {projects})')
    parser.add_argument('-lt', '--listing-type', type=str, help='Listing type to scrape (from "rent", "sale")')
    parser.add_argument('-b', '--batch-id', type=str, help='Batch ID')

    args = vars(parser.parse_args())

    project = args['project']
    batch_id = args['batch_id'] or f'{datetime.now():%Y%m%d}'
    listing_type = args['listing_type']

    return project, listing_type, batch_id


def construct_parquet_data_adls_path(project: str, listing_type: str, batch_id: str, data_layer: Literal['raw', 'transformed']) -> str:
    batch_id_date = datetime.strptime(batch_id, "%Y%m%d").date()

    filename = f'{project}_listings_{listing_type}_{data_layer}_{batch_id}'
    location = f'{listing_type}/{project}/{batch_id_date.year}/{batch_id_date.month}/{batch_id_date.day}'

    return f'{location}/{filename}.parquet'


def load_component_class(project_name: str, component_type: str) -> type[Any]:
    module_path = f'src.demo.scrapers.{project_name}.{component_type}'

    if component_type == 'scraper':
        expected_base_class = BaseScraper
    elif component_type == 'transformation':
        expected_base_class = BaseTransformation
    else:
        raise ValueError(f"Unknown component type: {component_type}")

    try:
        module = importlib.import_module(module_path)
        logger.debug(f"Successfully imported module: {module_path}")
    except ImportError as e:
        logger.exception(f"Could not import module {module_path}: {e}")
        raise ValueError(f"Project '{project_name}' {component_type} not found at '{module_path}'.") from e

    # Find the class within the module that inherits from the expected base class
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, expected_base_class) and obj is not expected_base_class:
            logger.debug(f"Found class {name} inheriting from {expected_base_class.__name__} in {module_path}")
            return obj

    raise ValueError(f"No valid {component_type} class found for project {project_name} in module {module_path}. "
                     f"Expected a class inheriting from {expected_base_class.__name__}.")


load_scraper_component = partial(load_component_class, component_type='scraper')
load_transformation_component = partial(load_component_class, component_type='transformation')

construct_raw_parquet_data_adls_path = partial(construct_parquet_data_adls_path, data_layer='raw')
construct_transformed_parquet_data_adls_path = partial(construct_parquet_data_adls_path, data_layer='transformed')
