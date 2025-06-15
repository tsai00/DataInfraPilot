import asyncio
import os

import pandas as pd

from src.demo.orchestration.utils import construct_raw_parquet_data_adls_path, load_scraper_component, parse_args
from src.demo.scrapers.base_scraper import ScraperError, ScraperRunMetadata
from src.demo.storage.adls_storage import ADLSStorage
from src.demo.storage.postgres_storage import PostgresStorage


async def main() -> None:
    adls_account_name = os.environ.get('ADLS_ACCOUNT_NAME')
    container_name = os.environ.get('ADLS_CONTAINER_NAME')

    pg_host = os.environ.get('POSTGRES_HOST')
    pg_db_name = os.environ.get('POSTGRES_DB_NAME')
    pg_user = os.environ.get('POSTGRES_USER')
    pg_password = os.environ.get('POSTGRES_PASSWORD')
    concurrency = int(os.environ.get('SCRAPING_CONCURRENCY', 10))

    project, listing_type, batch_id = parse_args()

    ScraperClass = load_scraper_component(project)  # noqa: N806 (keep upper case for better visibility)

    try:
        async with ScraperClass(listing_type=listing_type) as async_scraper:
            listings = await async_scraper.scrape_async(concurrency)
            df = pd.DataFrame(listings)
            run_metadata: ScraperRunMetadata = async_scraper.scraper_run_metadata

    except ScraperError as e:
        raise ValueError(f'Scraper for {project} ({listing_type}) failed: {e}') from e
    except Exception as e:
        raise ValueError(f'Unknown exception while scraping {project} ({listing_type}): {e}') from e

    with PostgresStorage(db_name=pg_db_name, user=pg_user, password=pg_password, host=pg_host) as postgres_storage:
        run_metadata_df = pd.DataFrame([run_metadata.to_dict()])
        postgres_storage.upload_data(run_metadata_df, 'scraper_run_metadata')

    raw_data_path = construct_raw_parquet_data_adls_path(project, listing_type, batch_id)
    metadata_path = f'{raw_data_path[: raw_data_path.rindex("/")]}/_metadata.json'

    with ADLSStorage(account_name=adls_account_name, container_name=container_name) as adls_storage:
        adls_storage.upload_df_to_parquet(df, path=raw_data_path)
        adls_storage.upload_data(run_metadata.to_dict(), path=metadata_path)

    df.to_excel(raw_data_path[raw_data_path.rindex('/') + 1 :].replace('.parquet', '.xlsx'))


if __name__ == '__main__':
    asyncio.run(main())
