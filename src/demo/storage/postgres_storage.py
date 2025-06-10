from typing import Literal

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
import pandas as pd

from src.demo.storage.base_storage import BaseStorage


class PostgresStorage(BaseStorage[pd.DataFrame]):
    def __init__(self, db_name: str, user: str, password: str, host: str, port: int = 5432):
        if not all([db_name, user, password, host]):
            raise ValueError("All PostgreSQL connection parameters (db_name, user, password, host) must be provided.")

        self.db_name = db_name
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.engine = None

        super().__init__('PostgresStorage')

    def __enter__(self):
        try:
            connection_string = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"
            self.engine = create_engine(connection_string)

            if not self.health_check():
                raise ValueError(f'Health check failed for DB "{self.db_name}" in {self.host}')

            self._logger.debug(f"PostgreSQL engine created for {self.user}@{self.host}:{self.port}/{self.db_name}")
            return self
        except Exception as e:
            self._logger.error(f"Failed to create PostgreSQL engine: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.engine:
            self.engine.dispose()
            self._logger.debug("PostgreSQL engine disposed.")

    def health_check(self) -> bool:
        if self.engine is None:
            self._logger.error("PostgreSQL engine not initialized.")
            return False
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            self._logger.debug("PostgreSQL health check successful.")
            return True
        except OperationalError as e:
            self._logger.error(f"PostgreSQL health check failed: Operational error. Check host, port, credentials. {e}")
            return False
        except ProgrammingError as e:
            self._logger.error(f"PostgreSQL health check failed: Programming error. Check database name, user permissions. {e}")
            return False
        except Exception as e:
            self._logger.error(f"PostgreSQL health check failed: Unexpected error. {e}")
            return False

    def upload_data(self, data: pd.DataFrame, path: str, if_exists: Literal["fail", "replace", "append"] = 'append') -> int:
        if self.engine is None:
            raise RuntimeError("PostgreSQL engine is not initialized. Use a 'with' statement.")

        if not isinstance(data, pd.DataFrame):
            # The BaseStorage generic type T already handles this at a type-hinting level,
            # but keeping this for runtime check
            raise ValueError('PostgresStorage currently only supports uploading DataFrame data')

        if data.empty:
            self._logger.warning(f"Attempted to upload an empty DataFrame to PostgreSQL table '{path}'. Skipping.")
            return 0

        try:
            rows_before = 0
            if if_exists == 'append':
                with self.engine.connect() as connection:
                    table_exists_query = text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '{path}');")
                    table_exists = connection.execute(table_exists_query).scalar()
                    if table_exists:
                        result = connection.execute(text(f"SELECT COUNT(*) FROM {path}")).scalar()
                        if result is not None:
                            rows_before = result

            data.to_sql(path, self.engine, if_exists=if_exists, index=False)
            rows_after = 0
            with self.engine.connect() as connection:
                result = connection.execute(text(f"SELECT COUNT(*) FROM {path}")).scalar()
                if result is not None:
                    rows_after = result

            rows_saved = rows_after - rows_before if if_exists == 'append' else len(data)
            self._logger.info(f"Successfully uploaded {rows_saved}/{len(data)} rows to PostgreSQL table '{path}'.")
            return rows_saved
        except ProgrammingError as e:
            self._logger.error(f"PostgreSQL upload failed: Programming error. Check table '{path}' existence/schema, user permissions. {e}")
            raise
        except OperationalError as e:
            self._logger.error(f"PostgreSQL upload failed: Operational error. Check database connection/credentials. {e}")
            raise
        except Exception as e:
            self._logger.error(f"An unexpected error occurred during PostgreSQL upload: {e}")
            raise

    def download_data(self, path: str, **kwargs) -> pd.DataFrame:
        if self.engine is None:
            raise RuntimeError("PostgreSQL engine is not initialized. Use a 'with' statement or call __enter__ first.")

        query_or_table = path

        try:
            self._logger.info(f"Attempting to download data from PostgreSQL using path/query: {query_or_table}")

            dataframe = pd.read_sql(query_or_table, self.engine, **kwargs)

            self._logger.info(f"Successfully downloaded {len(dataframe)} rows from PostgreSQL using path/query: {query_or_table}")
            return dataframe
        except OperationalError as e:
            self._logger.error(f"PostgreSQL download failed: Operational error. Check host, port, credentials. {e}")
            raise
        except ProgrammingError as e:
            self._logger.error(f"PostgreSQL download failed: Programming error. Check table '{query_or_table}' existence/permissions or query syntax. {e}")
            raise
        except Exception as e:
            self._logger.error(f"An unexpected error occurred during PostgreSQL download from {query_or_table}: {e}")
            raise