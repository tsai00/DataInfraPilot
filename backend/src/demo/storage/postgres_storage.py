from types import TracebackType
from typing import Literal

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from src.demo.storage.base_storage import BaseStorage


class PostgresStorage(BaseStorage[pd.DataFrame]):
    def __init__(self, db_name: str, user: str, password: str, host: str, port: int = 5432) -> None:
        if not all([db_name, user, password, host]):
            raise ValueError('All PostgreSQL connection parameters (db_name, user, password, host) must be provided.')

        self.db_name = db_name
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.engine = None

        super().__init__('PostgresStorage')

    def __enter__(self) -> 'PostgresStorage':
        try:
            connection_string = (
                f'postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}'
            )
            self.engine = create_engine(connection_string)

            if not self.health_check():
                raise ValueError(f'Health check failed for DB "{self.db_name}" in {self.host}')

            self._logger.debug(f'PostgreSQL engine created for {self.user}@{self.host}:{self.port}/{self.db_name}')
            return self
        except Exception:
            self._logger.exception('Failed to create PostgreSQL engine.')
            raise

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        if self.engine:
            self.engine.dispose()
            self._logger.debug('PostgreSQL engine disposed.')

    def health_check(self) -> bool:
        if self.engine is None:
            self._logger.exception('PostgreSQL engine not initialized.')
            return False
        try:
            with self.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            self._logger.debug('PostgreSQL health check successful.')
            return True
        except OperationalError:
            self._logger.exception('PostgreSQL health check failed: Operational error. Check host, port, credentials.')
            return False
        except ProgrammingError:
            self._logger.exception(
                'PostgreSQL health check failed: Programming error. Check database name, user permissions.'
            )
            return False
        except Exception:
            self._logger.exception('PostgreSQL health check failed: Unexpected error.')
            return False

    def upload_data(
        self, data: pd.DataFrame, path: str, if_exists: Literal['fail', 'replace', 'append'] = 'append'
    ) -> int:
        if self.engine is None:
            raise RuntimeError("PostgreSQL engine is not initialized. Use a 'with' statement.")

        if not isinstance(data, pd.DataFrame):
            # The BaseStorage generic type T already handles this at a type-hinting level,
            # but keeping this for runtime check
            raise TypeError('PostgresStorage currently only supports uploading DataFrame data')

        if data.empty:
            self._logger.warning(f"Attempted to upload an empty DataFrame to PostgreSQL table '{path}'. Skipping.")
            return 0

        try:
            rows_before = 0
            if if_exists == 'append':
                with self.engine.connect() as connection:
                    table_exists_query = text(
                        f'SELECT EXISTS ('  # noqa: S608 (no user input)
                        f'SELECT 1 FROM information_schema.tables '
                        f"WHERE table_schema = 'public' "
                        f"AND table_name = '{path}');"
                    )
                    table_exists = connection.execute(table_exists_query).scalar()
                    if table_exists:
                        result = connection.execute(text(f'SELECT COUNT(*) FROM {path}')).scalar()  # noqa: S608 (no user input)
                        if result is not None:
                            rows_before = result

            data.to_sql(path, self.engine, if_exists=if_exists, index=False)
            rows_after = 0
            with self.engine.connect() as connection:
                result = connection.execute(text(f'SELECT COUNT(*) FROM {path}')).scalar()  # noqa: S608 (no user input)
                if result is not None:
                    rows_after = result

            rows_saved = rows_after - rows_before if if_exists == 'append' else len(data)
            self._logger.info(f"Successfully uploaded {rows_saved}/{len(data)} rows to PostgreSQL table '{path}'.")
            return rows_saved
        except ProgrammingError:
            self._logger.exception(
                f"PostgreSQL upload failed: Programming error. Check table '{path}' existence/schema, user permissions."
            )
            raise
        except OperationalError:
            self._logger.exception(
                'PostgreSQL upload failed: Operational error. Check database connection/credentials.'
            )
            raise
        except Exception:
            self._logger.exception('An unexpected error occurred during PostgreSQL upload')
            raise

    def download_data(self, path: str) -> pd.DataFrame:
        if self.engine is None:
            raise RuntimeError("PostgreSQL engine is not initialized. Use a 'with' statement or call __enter__ first.")

        query_or_table = path

        try:
            self._logger.info(f'Attempting to download data from PostgreSQL using path/query: {query_or_table}')

            dataframe = pd.read_sql(query_or_table, self.engine)

            self._logger.info(
                f'Successfully downloaded {len(dataframe)} rows from PostgreSQL using path/query: {query_or_table}'
            )
            return dataframe
        except OperationalError:
            self._logger.exception('PostgreSQL download failed: Operational error. Check host, port, credentials.')
            raise
        except ProgrammingError:
            self._logger.exception(
                f'PostgreSQL download failed: Programming error. '
                f"Check table '{query_or_table}' existence/permissions or query syntax."
            )
            raise
        except Exception:
            self._logger.exception(f'An unexpected error occurred during PostgreSQL download from {query_or_table}')
            raise
