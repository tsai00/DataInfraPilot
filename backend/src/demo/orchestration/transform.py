import os

from src.demo.orchestration.utils import (
    construct_raw_parquet_data_adls_path,
    construct_transformed_parquet_data_adls_path,
    load_transformation_component,
    parse_args,
)
from src.demo.scrapers.base_transformation import TransformationError
from src.demo.storage.adls_storage import ADLSStorage


def main() -> None:
    adls_account_name = os.environ.get('ADLS_ACCOUNT_NAME')
    container_name = os.environ.get('ADLS_CONTAINER_NAME')

    project, listing_type, batch_id = parse_args()

    TransformationClass = load_transformation_component(project)  # noqa: N806 (keep upper case for better visibility)

    raw_data_path = construct_raw_parquet_data_adls_path(project, listing_type, batch_id)
    transformed_data_path = construct_transformed_parquet_data_adls_path(project, listing_type, batch_id)

    with ADLSStorage(account_name=adls_account_name, container_name=container_name) as adls_storage:
        df_raw = adls_storage.download_parquet_to_df(raw_data_path)

        try:
            transformation = TransformationClass()

            df_transformed = transformation.transform(df_raw)

            df_transformed['_data_source'] = project.capitalize()

            df_transformed.to_excel(
                transformed_data_path[transformed_data_path.rindex('/') + 1 :].replace('.parquet', '.xlsx')
            )

        except TransformationError as e:
            raise ValueError(f'Transformation for {project} ({listing_type}) failed: {e}') from e
        except Exception as e:
            raise ValueError(f'Unknown exception while transforming data for {project} ({listing_type}): {e}') from e

        adls_storage.upload_df_to_parquet(df_transformed, path=transformed_data_path)


if __name__ == '__main__':
    main()
