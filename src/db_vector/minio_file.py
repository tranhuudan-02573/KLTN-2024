from __future__ import annotations

import os
import tempfile
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Union

from langchain_community.document_loaders.unstructured import UnstructuredBaseLoader
from minio import Minio
from minio.error import S3Error

if TYPE_CHECKING:
    from minio.datatypes import Object as MinioObject


class MinioFileLoader(UnstructuredBaseLoader):
    """Load from Minio file."""

    def __init__(
            self,
            bucket: str,
            key: str,
            *,
            endpoint: str,
            access_key: str,
            secret_key: str,
            secure: bool = False,
            region: Optional[str] = None,
            http_client: Optional[Any] = None,
            mode: str = "single",
            post_processors: Optional[List[Callable]] = None,
            **unstructured_kwargs: Any,
    ):
        """Initialize with bucket and key name.

        :param bucket: The name of the Minio bucket.
        :param key: The key of the Minio object.
        :param endpoint: Minio server endpoint.
        :param access_key: Minio access key.
        :param secret_key: Minio secret key.
        :param secure: Use secure (TLS) connection.
        :param region: Minio region name.
        :param http_client: Custom HTTP client object.
        :param mode: Mode in which to read the file. Valid options are: single,
            paged and elements.
        :param post_processors: Post processing functions to be applied to
            extracted elements.
        :param **unstructured_kwargs: Arbitrary additional kwargs to pass in when
            calling `partition`
        """
        super().__init__(mode, post_processors, **unstructured_kwargs)
        self.bucket = bucket
        self.key = key
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.region = region
        self.http_client = http_client

    def _get_elements(self) -> List:
        """Get elements."""
        from unstructured.partition.auto import partition

        minio_client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
            region=self.region,
            http_client=self.http_client,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, os.path.basename(self.key))
            try:
                minio_client.fget_object(self.bucket, self.key, file_path)
                return partition(filename=file_path, **self.unstructured_kwargs)
            except S3Error as e:
                raise ValueError(f"Error downloading file from Minio: {str(e)}")

    def _get_metadata(self) -> dict:
        return {"source": f"minio://{self.bucket}/{self.key}"}
