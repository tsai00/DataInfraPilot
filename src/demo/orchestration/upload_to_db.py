import os

from src.demo.orchestration.utils import parse_args, construct_transformed_parquet_data_adls_path
from src.demo.storage.adls_storage import ADLSStorage
from src.demo.storage.postgres_storage import PostgresStorage


def main() -> None:
    adls_account_name = os.environ.get('ADLS_ACCOUNT_NAME')
    container_name = os.environ.get('ADLS_CONTAINER_NAME')

    pg_host = os.environ.get('POSTGRES_HOST')
    pg_db_name = os.environ.get('POSTGRES_DB_NAME')
    pg_user = os.environ.get('POSTGRES_USER')
    pg_password = os.environ.get('POSTGRES_PASSWORD')

    project, listing_type, batch_id = parse_args()

    transformed_data_path = construct_transformed_parquet_data_adls_path(project, listing_type, batch_id)

    with ADLSStorage(account_name=adls_account_name, container_name=container_name) as adls_storage:
        df_transformed = adls_storage.download_parquet_to_df(transformed_data_path)

    with PostgresStorage(db_name=pg_db_name, user=pg_user, password=pg_password, host=pg_host) as postgres_storage:
        postgres_storage.upload_data(df_transformed, listing_type)


if __name__ == '__main__':
    main()
