import io
import json
from types import TracebackType, UnionType

import pandas as pd
from azure.core.exceptions import AzureError, ClientAuthenticationError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from src.demo.storage.base_storage import BaseStorage

ADLSIOType: UnionType = dict | str | bytes | io.BytesIO


class ADLSStorage(BaseStorage[ADLSIOType]):
    def __init__(self, account_name: str, container_name: str) -> None:
        if not account_name:
            raise ValueError('ADLS account name cannot be empty.')
        if not container_name:
            raise ValueError('ADLS container name cannot be empty.')

        self.account_url = f'https://{account_name}.blob.core.windows.net'
        self.container_name = container_name
        self.blob_service_client: BlobServiceClient | None = None

        super().__init__('ADLSStorage')

    def __enter__(self) -> 'ADLSStorage':
        try:
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(self.account_url, credential=credential)

            if not self.health_check():
                raise ValueError(
                    f'Health check failed for container "{self.container_name}" in account {self.account_url}'
                )

            self._logger.debug(f'ADLS BlobServiceClient initialized for account: {self.account_url}')
            return self
        except ClientAuthenticationError:
            self._logger.exception(
                'Azure authentication failed. Ensure accessing identity is configured correctly and '
                'has Storage Blob Data Contributor role.'
            )
            raise
        except Exception:
            self._logger.exception('Failed to initialize ADLS BlobServiceClient')
            raise

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        if self.blob_service_client:
            self.blob_service_client.close()

    def health_check(self) -> bool:
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.get_container_properties()
            self._logger.debug(f"ADLS health check successful for container '{self.container_name}'.")
            return True
        except ClientAuthenticationError:
            self._logger.exception('ADLS health check failed: Authentication error. Ensure correct permissions.')
            return False
        except ResourceNotFoundError:
            self._logger.exception(
                f"ADLS health check failed: Container '{self.container_name}' not found. Please create it."
            )
            return False
        except AzureError:
            self._logger.exception('ADLS health check failed due to Azure error')
            return False
        except Exception:
            self._logger.exception('ADLS health check failed due to unexpected error')
            return False

    def upload_data(self, data: ADLSIOType, path: str) -> str:
        if self.blob_service_client is None:
            raise RuntimeError("ADLS BlobServiceClient is not initialized. Use a 'with' statement.")

        if isinstance(data, dict):
            data = json.dumps(data, indent=4)

        try:
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=path)
            blob_client.upload_blob(data, overwrite=True)
            self._logger.info(f'Data successfully uploaded to ADLS at: {self.container_name}/{path}')
            return f'{self.container_name}/{path}'
        except AzureError:
            self._logger.exception(f'Failed to upload data to ADLS at {self.container_name}/{path}')
            raise
        except Exception:
            self._logger.exception('An unexpected error occurred during ADLS upload')
            raise

    def download_data(self, path: str) -> ADLSIOType:
        if self.blob_service_client is None:
            raise RuntimeError("ADLS BlobServiceClient is not initialized. Use a 'with' statement.")

        try:
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=path)
            download_stream = blob_client.download_blob()
            buffer = io.BytesIO()
            download_stream.readinto(buffer)
            buffer.seek(0)

            self._logger.info(f'Data successfully downloaded from ADLS at: {self.container_name}/{path}')
            return buffer
        except ResourceNotFoundError:
            self._logger.warning(f'File not found at {self.container_name}/{path}. Returning empty string.')
            return ''
        except AzureError:
            self._logger.exception(f'Failed to download file from ADLS at {self.container_name}/{path}')
            raise
        except Exception:
            self._logger.exception('An unexpected error occurred during ADLS download')
            raise

    def upload_df_to_parquet(self, dataframe: pd.DataFrame, path: str) -> str:
        if dataframe.empty:
            self._logger.warning(f'Attempted to upload an empty DataFrame to {self.container_name}/{path}. Skipping.')
            return ''

        buffer = io.BytesIO()
        dataframe.to_parquet(buffer, index=False)
        buffer.seek(0)

        return self.upload_data(buffer, path=path)

    def download_parquet_to_df(self, path: str) -> pd.DataFrame:
        buffer = self.download_data(path)

        return pd.read_parquet(buffer)
