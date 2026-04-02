"""Alibaba Cloud OSS (Object Storage Service) connector for file operations.

Provides high-level interface for uploading, downloading, copying, and managing files
on Alibaba Cloud OSS with retry logic and error handling.

Supports multiple OSS connections by specifying a db_type that maps to configuration
in app.configs.config.oss_config.

Usage:
    from app.connections.oss import OSSConnector

    # Basic usage with context manager (recommended)
    with OSSConnector("negative_list") as connector:
        connector.upload_object("local_file.parquet", "remote/path/file.parquet")
        df = connector.refresh_data("file.parquet", "path/in/oss/", "./local/path/")

    # Standalone usage (manual lifecycle management)
    connector = OSSConnector("negative_list")
    files = connector.list_object("directory/prefix/")
    success = connector.download_object("remote/file.parquet", "./local/file.parquet")

Configuration:
    Requires credentials in app.configs.config.oss_config[db_type]:
        - access_key_id: Alibaba Cloud Access Key ID
        - access_key_secret: Alibaba Cloud Access Key Secret
        - bucket_name: OSS bucket name
        - endpoint: OSS endpoint URL (e.g., oss-cn-hangzhou.aliyuncs.com)
        - region: OSS region (optional, for metadata)

Error Handling:
    - All methods return False or empty list on error (no exceptions raised to caller)
    - All errors are logged at ERROR or WARNING level
    - Retry logic with exponential backoff for download operations
    - Missing files and invalid paths are validated early

Template Customization:
    To use in another workspace:
    1. Copy this file to your project's app/connections/ directory
    2. Update oss_config in app/configs/config.py with your OSS credentials
    3. Add new db_type keys to oss_config for different OSS buckets
    4. Optionally customize max_retries and retry_delay parameters
"""

import os
import time
from typing import Any

import oss2
import pandas as pd

from app.configs.config import oss_config

# Try to import logger from log_config; use standard logging if not available
try:
    from app.configs.log_config import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class OSSConnector:
    """Handles upload/download operations for Alibaba Cloud OSS.

    Attributes:
        config: Configuration dict for the OSS bucket
        access_key_id: Access Key ID for authentication
        access_key_secret: Access Key Secret for authentication
        bucket_name: Name of the OSS bucket
        endpoint: OSS endpoint URL
        region: OSS region name
        auth: OSS Auth object
        bucket: OSS Bucket object for operations
    """

    def __init__(self, db_type: str, config_path: str | None = None) -> None:
        """Initialize OSS connection using credentials from the application config.

        Args:
            db_type: Key into oss_config (e.g., 'negative_list'). Must exist in config.
            config_path: DEPRECATED - retained for backwards compatibility. Not used.

        Raises:
            ValueError: If db_type not found in oss_config or credentials are empty.

        Example:
            connector = OSSConnector("negative_list")
        """
        if db_type not in oss_config:
            raise ValueError(f"OSS config key not found: {db_type}. Available keys: {list(oss_config.keys())}")

        self.config: dict[str, Any] = oss_config[db_type]
        logger.debug("Initializing OSSConnector for db_type={}, config={}", db_type, self.config)

        self.access_key_id: str = self.config.get("access_key_id", "")
        self.access_key_secret: str = self.config.get("access_key_secret", "")
        self.bucket_name: str = self.config.get("bucket_name", "")
        self.endpoint: str = self.config.get("endpoint", "")
        self.region: str = self.config.get("region", "")

        # Validate credentials presence
        if not self.access_key_id or not self.access_key_secret:
            raise ValueError(
                "OSS access_key_id and access_key_secret must not be empty. "
                "Check your configuration in app/configs/config.py"
            )
        if not self.bucket_name or not self.endpoint:
            raise ValueError(
                "OSS bucket_name and endpoint must not be empty. "
                "Check your configuration in app/configs/config.py"
            )

        self.auth: oss2.Auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        self.bucket: oss2.Bucket = oss2.Bucket(self.auth, self.endpoint, self.bucket_name)

    def __enter__(self) -> "OSSConnector":
        """Context manager entry - return self for use in with statement."""
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any | None) -> None:
        """Context manager exit - cleanup if needed.

        Args:
            exc_type: Exception type if exception occurred
            exc_val: Exception value if exception occurred
            exc_tb: Exception traceback if exception occurred
        """
        if exc_type:
            logger.error("Exception in OSS context: {}", exc_val)
        # OSS connections don't need explicit cleanup, but we log errors

    def list_object(self, directory_prefix: str) -> list[str]:
        """List all objects inside a specified directory (prefix) in OSS.

        Args:
            directory_prefix: Directory prefix to search (e.g., "data/folder/")

        Returns:
            List of object keys (paths) found in the directory.
            Returns empty list if no objects found or error occurs.

        Example:
            files = connector.list_object("reports/2024/")
            for file in files:
                print(f"Found: {file}")
        """
        try:
            file_list: list[str] = []
            for obj in oss2.ObjectIterator(self.bucket, prefix=directory_prefix):
                file_list.append(obj.key)

            if file_list:
                logger.info("Found {} objects in prefix: {}", len(file_list), directory_prefix)
                for file in file_list[:5]:  # Log first 5
                    logger.debug("   - {}", file)
            else:
                logger.info("No objects found in prefix: {}", directory_prefix)

            return file_list

        except oss2.exceptions.OssError as e:
            logger.error("OSS list_object failed for prefix={}: {}", directory_prefix, e)
            return []
        except Exception as e:
            logger.error("Unexpected error in list_object: {}", e)
            return []

    def upload_object(self, local_file_path: str, oss_object_path: str) -> bool:
        """Upload a local file to OSS.

        Args:
            local_file_path: Full path to local file to upload
            oss_object_path: Target path in OSS (e.g., "data/folder/file.parquet")

        Returns:
            True if upload successful, False otherwise.

        Example:
            success = connector.upload_object("./output.csv", "results/output.csv")
        """
        if not os.path.exists(local_file_path):
            logger.error("Local file does not exist: {}", local_file_path)
            return False

        if not oss_object_path or oss_object_path.strip() == "":
            logger.error("OSS object path cannot be empty")
            return False

        try:
            self.bucket.put_object_from_file(oss_object_path, local_file_path)
            logger.info("Uploaded: {} -> {}", local_file_path, oss_object_path)
            return True
        except oss2.exceptions.OssError as e:
            logger.error("OSS upload failed: {}", e)
            return False
        except Exception as e:
            logger.error("Upload failed: {}", e)
            return False

    def download_object(
        self, oss_object_path: str, local_file_path: str, max_retries: int = 3, retry_delay: float = 1.0
    ) -> bool:
        """Download a file from OSS with retry logic.

        Args:
            oss_object_path: Path in OSS to download (e.g., "data/folder/file.parquet")
            local_file_path: Target path for local download
            max_retries: Number of retry attempts (default: 3)
            retry_delay: Initial delay between retries in seconds (default: 1.0)

        Returns:
            True if download successful, False otherwise.

        Example:
            success = connector.download_object("data/input.parquet", "./input.parquet")
        """
        if not oss_object_path or oss_object_path.strip() == "":
            logger.error("OSS object path cannot be empty")
            return False

        # Create directory if it doesn't exist
        local_dir = os.path.dirname(local_file_path)
        if local_dir and not os.path.exists(local_dir):
            try:
                os.makedirs(local_dir, exist_ok=True)
            except Exception as e:
                logger.error("Failed to create directory {}: {}", local_dir, e)
                return False

        for attempt in range(max_retries):
            try:
                # Check if object exists first
                if not self.bucket.object_exists(oss_object_path):
                    logger.error("Object does not exist in OSS: {}", oss_object_path)
                    return False

                self.bucket.get_object_to_file(oss_object_path, local_file_path)
                logger.info("Downloaded: {} -> {}", oss_object_path, local_file_path)
                return True
            except oss2.exceptions.OssError as e:
                logger.warning("OSS download attempt {}/{} failed: {}", attempt + 1, max_retries, e)
                if attempt < max_retries - 1:
                    backoff = retry_delay * (2 ** attempt)  # Exponential backoff
                    time.sleep(backoff)
                else:
                    logger.error("OSS download failed after {} attempts: {}", max_retries, e)
            except Exception as e:
                logger.error("Download failed: {}", e)
                return False

        return False

    def delete_object(self, oss_object_path: str, confirm: bool = False) -> bool:
        """Delete a file from OSS with safety confirmation.

        Args:
            oss_object_path: Path in OSS to delete
            confirm: Must be True to perform deletion (safety check)

        Returns:
            True if deletion successful, False otherwise.

        Example:
            success = connector.delete_object("temp/old_file.parquet", confirm=True)
        """
        if not oss_object_path or oss_object_path.strip() == "":
            logger.error("OSS object path cannot be empty")
            return False

        if not confirm:
            logger.warning("Delete operation requires confirm=True for: {}", oss_object_path)
            return False

        try:
            # Check if object exists first
            if not self.bucket.object_exists(oss_object_path):
                logger.warning("Object does not exist, cannot delete: {}", oss_object_path)
                return False

            self.bucket.delete_object(oss_object_path)
            logger.info("Deleted: {}", oss_object_path)
            return True
        except oss2.exceptions.OssError as e:
            logger.error("OSS deletion failed: {}", e)
            return False
        except Exception as e:
            logger.error("Deletion failed: {}", e)
            return False

    def copy_object(self, source_key: str, target_key: str) -> bool:
        """Copy a file within OSS bucket.

        Args:
            source_key: Source object path in OSS
            target_key: Target object path in OSS

        Returns:
            True if copy successful, False otherwise.

        Example:
            success = connector.copy_object("original/file.parquet", "backup/file.parquet")
        """
        try:
            self.bucket.copy_object(
                source_bucket_name=self.bucket_name,
                source_key=source_key,
                target_key=target_key,
            )
            logger.info("Copied {} to {}", source_key, target_key)
            return True
        except Exception as e:
            logger.error("Copy failed: {}", e)
            return False

    def refresh_data(
        self, file_name: str, oss_path: str, local_path: str, force_download: bool = False
    ) -> pd.DataFrame:
        """Smart data synchronization with caching and freshness check.

        Strategy:
            1. Return from local cache if file exists and is fresh
            2. Download from OSS if local file doesn't exist
            3. Download if OSS file is newer than local file

        Args:
            file_name: Name of the file (e.g., "data.parquet")
            oss_path: Directory path in OSS (e.g., "data/folder/")
            local_path: Local directory path (e.g., "./local/data/")
            force_download: If True, skip cache and download from OSS

        Returns:
            Loaded pandas DataFrame, or empty DataFrame if operation fails.

        Example:
            df = connector.refresh_data(
                "report.parquet",
                "data/reports/",
                "./local_data/"
            )
        """
        if not file_name or not oss_path or not local_path:
            logger.error("All parameters required: file_name, oss_path, local_path")
            return pd.DataFrame()

        # Ensure paths end with separator
        if not oss_path.endswith("/"):
            oss_path += "/"
        if not local_path.endswith("/"):
            local_path += "/"

        oss_object_path = oss_path + file_name
        local_file_path = local_path + file_name

        try:
            should_download = force_download or not os.path.exists(local_file_path)

            # Check if OSS file is newer than local file
            if not should_download:
                try:
                    oss_obj = self.bucket.get_object_meta(oss_object_path)
                    oss_modified = oss_obj.last_modified
                    local_modified = os.path.getmtime(local_file_path)

                    if oss_modified and oss_modified > local_modified:
                        logger.info("OSS file is newer, will download: {}", file_name)
                        should_download = True
                except oss2.exceptions.NoSuchKey:
                    logger.error("OSS object not found: {}", oss_object_path)
                    return pd.DataFrame()
                except Exception as e:
                    logger.warning("Could not compare file timestamps: {}", e)

            if should_download:
                if not self.download_object(
                    oss_object_path=oss_object_path, local_file_path=local_file_path
                ):
                    logger.error("Failed to download: {}", oss_object_path)
                    return pd.DataFrame()

            # Validate file exists and is readable
            if not os.path.exists(local_file_path):
                logger.error("Local file not found after download: {}", local_file_path)
                return pd.DataFrame()

            file_size = os.path.getsize(local_file_path)
            if file_size == 0:
                logger.warning("Downloaded file is empty: {}", local_file_path)
                return pd.DataFrame()

            logger.info("Reading parquet file: {} ({} bytes)", local_file_path, file_size)
            return pd.read_parquet(local_file_path)

        except pd.errors.ParserError as e:
            logger.error("Failed to parse parquet file: {}", e)
            return pd.DataFrame()
        except Exception as e:
            logger.error("Refresh data failed: {}", e)
            return pd.DataFrame()
