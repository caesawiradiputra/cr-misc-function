"""PVC Data Manager for optimized data sharing between DAG tasks.

Provides utilities to use PVC (Persistent Volume Claim) for data sharing instead of
repeatedly downloading/uploading files to/from OSS between pipeline steps.

Architecture:
    - Kubernetes environments use /shared-data PVC mount for fast local access
    - Local development uses ./shared-data directory
    - Each process maintains isolated subdirectories (temp, upload, models, mapping, baseline)
    - Task output caching allows skipping re-processing of recent outputs

Directory Structure:
    /shared-data/
    ├── my_process/
    │   ├── temp/          # Intermediate processing results
    │   ├── upload/        # Files ready for upload to OSS
    │   ├── models/        # ML models or reference data
    │   ├── mapping/       # Lookup tables and mappings
    │   └── baseline/      # Historical baselines for comparison
    └── other_process/
        ├── temp/
        └── ...

Caching Strategy:
    When ENABLE_TASK_OUTPUT_CACHE=true:
        - Check if output files exist and are younger than TASK_OUTPUT_CACHE_HOURS
        - Skip task execution if cache is fresh
        - Automatically removes stale files during cleanup
        - Prevents redundant computations in DAG retries or reruns

Template Customization:
    To use in another workspace:
    1. Copy this file to your project's app/utils/ directory
    2. Ensure app/configs/config.py has ENABLE_TASK_OUTPUT_CACHE and TASK_OUTPUT_CACHE_HOURS
    3. Update your DAG tasks to use PVCDataManager for data sharing
    4. In Kubernetes: Mount PVC as /shared-data
    5. In local dev: Create ./shared-data directory or it will be created automatically
"""

import fnmatch
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from app.configs.config import (
    ENABLE_TASK_OUTPUT_CACHE,
    TASK_OUTPUT_CACHE_HOURS,
)
from app.configs.log_config import init_logging, logger
from app.connections.oss import OSSConnector
from app.utils import load_parquet_safe

PROCESS_NAMES = "misc_function"

def _get_base_path() -> str:
    """Determine the base path for data storage based on environment.

    Returns:
        Base path for data storage.
    """
    kubernetes_pvc_path = "/shared-data"
    if os.path.exists(kubernetes_pvc_path):
        logger.info("Detected Kubernetes environment, using PVC mount")
        return kubernetes_pvc_path

    local_base_path = os.path.join(os.getcwd(), "shared-data")
    logger.info(
        f"Detected local environment, using local shared folder: {local_base_path}"
    )
    return local_base_path


PVC_BASE_PATH = _get_base_path()
PVC_TEMP_PATH = "temp"
PVC_UPLOAD_PATH = "upload"
PVC_MODELS_PATH = "models"
PVC_MAPPING_PATH = "mapping"
PVC_BASELINE_PATH = "baseline"


def get_process_paths(process_name: str = "misc_function") -> dict:
    """Get process-specific paths within the shared storage.

    Args:
        process_name: Name of the process/DAG.

    Returns:
        Dictionary of subdirectory paths for the process.
    """
    process_base = os.path.join(PVC_BASE_PATH, PROCESS_NAMES)

    return {
        "upload": os.path.join(process_base, "upload"),
        "temp": os.path.join(process_base, "temp"),
        "models": os.path.join(process_base, "models"),
        "mapping": os.path.join(process_base, "mapping"),
        "baseline": os.path.join(process_base, "baseline"),
    }


class PVCDataManager:
    """Manages data operations using PVC for efficient data sharing between DAG tasks."""

    def __init__(self, process_name: str = "misc_function") -> None:
        """Initialize PVC data manager for a specific process.

        Args:
            process_name: Name of the process/DAG for namespace isolation.
        """
        self.process_name = process_name
        self.is_local = not os.path.exists("/shared-data")
        self.base_path = PVC_BASE_PATH
        self.process_paths = get_process_paths(process_name)

        logger.info(
            f"PVCDataManager initialized - Process: {process_name}, Local mode: {self.is_local}, Base path: {self.base_path}"
        )
        self.ensure_pvc_directories()

    def ensure_pvc_directories(self):
        """Ensure all required process-specific directories exist."""
        for _, path_value in self.process_paths.items():
            os.makedirs(path_value, exist_ok=True)
            logger.debug(
                f"Ensured {'local' if self.is_local else 'PVC'} directory exists: {path_value}"
            )

    def get_environment_info(self) -> dict:
        """
        Get information about the current environment.

        Returns:
            dict: Environment information
        """
        return {
            "is_local": self.is_local,
            "process_name": self.process_name,
            "base_path": self.base_path,
            "platform": "Windows" if os.name == "nt" else "Linux/WSL",
            "available_paths": self.process_paths,
        }

    def get_pvc_path(self, subdirectory: str, filename: str) -> str:
        """Get the full PVC path for a file.

        Args:
            subdirectory: Subdirectory name (upload, temp, models, etc.).
            filename: Name of the file.

        Returns:
            Full path to the file in PVC.
        """
        if subdirectory not in self.process_paths:
            raise ValueError(
                f"Invalid subdirectory: {subdirectory}. Must be one of: {list(self.process_paths.keys())}"
            )

        return os.path.join(self.process_paths[subdirectory], filename)

    def file_exists_in_pvc(self, subdirectory: str, filename: str) -> bool:
        """Check if a file exists in PVC.

        Args:
            subdirectory: Subdirectory name.
            filename: Name of the file.

        Returns:
            True if file exists, False otherwise.
        """
        file_path = self.get_pvc_path(subdirectory, filename)
        exists = os.path.exists(file_path)
        logger.debug(f"File {filename} exists in PVC {subdirectory}: {exists}")
        return exists

    def save_to_pvc(
        self, df: pd.DataFrame, subdirectory: str, filename: str, save_csv: bool = False
    ) -> str:
        """Save DataFrame to PVC.

        Args:
            df: DataFrame to save.
            subdirectory: Subdirectory name.
            filename: Name of the file (should end with .parquet).
            save_csv: Also save as CSV for debugging.

        Returns:
            Path where file was saved.
        """
        pvc_path = self.get_pvc_path(subdirectory, filename)

        # Save as parquet
        df.to_parquet(pvc_path)
        logger.info(f"Saved to PVC: {pvc_path} (shape: {df.shape})")

        # Optionally save as CSV for debugging
        if save_csv:
            csv_path = pvc_path.replace(".parquet", ".csv")
            df.to_csv(csv_path)
            logger.info(f"Also saved CSV: {csv_path}")

        return pvc_path

    def load_from_pvc(self, subdirectory: str, filename: str) -> pd.DataFrame:
        """Load DataFrame from PVC.

        Args:
            subdirectory: Subdirectory name.
            filename: Name of the file.

        Returns:
            Loaded DataFrame or empty DataFrame if file not found.
        """
        pvc_path = self.get_pvc_path(subdirectory, filename)

        if not os.path.exists(pvc_path):
            logger.warning(f"File not found in PVC: {pvc_path}")
            return pd.DataFrame()

        try:
            df = load_parquet_safe(pvc_path)
            logger.info(f"Loaded from PVC: {pvc_path} (shape: {df.shape})")
            return df
        except Exception as e:
            logger.error(f"Failed to load from PVC {pvc_path}: {e}")
            return pd.DataFrame()

    def is_output_fresh(
        self,
        output_files: list[str],
        subdirectory: str = "temp",
        max_age_hours: int | None = None
    ) -> bool:
        """Check if task output files exist and are fresh enough to skip reprocessing.

        Args:
            output_files: List of output filenames to check.
            subdirectory: Subdirectory where files are stored.
            max_age_hours: Maximum age in hours. If None, uses TASK_OUTPUT_CACHE_HOURS from config.

        Returns:
            True if all output files exist and are fresh, False otherwise.
        """
        if not ENABLE_TASK_OUTPUT_CACHE:
            logger.info("Task output caching is disabled in config")
            return False

        max_age_hours = max_age_hours or TASK_OUTPUT_CACHE_HOURS
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        for filename in output_files:
            file_path = self.get_pvc_path(subdirectory, filename)

            if not os.path.exists(file_path):
                logger.info(f"Output file not found in PVC: {filename}")
                return False

            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            file_age_hours = (datetime.now() - file_mtime).total_seconds() / 3600

            if file_mtime < cutoff_time:
                logger.info(
                    f"Output file {filename} is too old ({file_age_hours:.1f} hours > {max_age_hours} hours)"
                )
                return False

            logger.info(
                f"Output file {filename} is fresh ({file_age_hours:.1f} hours old, modified: {file_mtime})"
            )

        logger.info(
            f"All {len(output_files)} output files are fresh (< {max_age_hours} hours old). Skipping task execution."
        )
        return True

    def get_data_with_fallback(
        self,
        filename: str,
        oss_path: str,
        oss_client: OSSConnector,
        subdirectory: str = "temp",
    ) -> pd.DataFrame:
        """Get data with PVC-first strategy and OSS fallback.

        Priority:
        1. Check PVC directory.
        2. Download from OSS if not in PVC.

        Args:
            filename: Name of the file.
            oss_path: OSS path where file is stored.
            oss_client: OSS client instance.
            subdirectory: PVC subdirectory to check.

        Returns:
            The loaded data.
        """
        # First, check if file exists in PVC
        if self.file_exists_in_pvc(subdirectory, filename):
            logger.info(f"Found {filename} in PVC, using shared data")
            return self.load_from_pvc(subdirectory, filename)

        # If not in PVC, download from OSS and save to PVC for next tasks
        logger.info(
            f"File {filename} not in PVC, downloading from OSS and saving to PVC"
        )
        oss_object_path = oss_path + filename
        pvc_path = self.get_pvc_path(subdirectory, filename)

        # Download from OSS directly to PVC
        if oss_client.download_object(oss_object_path, pvc_path):
            return self.load_from_pvc(subdirectory, filename)
        else:
            logger.error(f"Failed to download {filename} from OSS")
            return pd.DataFrame()

    def list_pvc_files(self, subdirectory: str, filter: str | None = None) -> list[str]:
        """List all files in a PVC subdirectory with optional filtering.

        Args:
            subdirectory: Subdirectory name.
            filter: Optional glob pattern to filter filenames (e.g., "*.parquet").

        Returns:
            List of full file paths in the directory.

        Example:
            >>> pvc_manager.list_pvc_files(PVC_TEMP_PATH, "*.parquet")
            ['/shared-data/process/temp/output.parquet']
        """
        if subdirectory not in self.process_paths:
            return []

        directory_path = self.process_paths[subdirectory]
        if not os.path.exists(directory_path):
            return []

        all_files = [
            os.path.join(directory_path, f)
            for f in os.listdir(directory_path)
            if os.path.isfile(os.path.join(directory_path, f))
        ]

        if filter:
            filtered_files = []
            for file_path in all_files:
                filename = os.path.basename(file_path)
                if fnmatch.fnmatch(filename, filter):
                    filtered_files.append(file_path)
            all_files = filtered_files

        logger.debug(f"Files in PVC {subdirectory} (filter='{filter}'): {[os.path.basename(f) for f in all_files]}")
        return all_files

    def cleanup_pvc_directory(
        self, subdirectory: str, keep_patterns: list[str] | None = None
    ):
        """Clean up files in a PVC subdirectory, optionally keeping files matching patterns.

        Args:
            subdirectory: Subdirectory to clean.
            keep_patterns: Patterns of files to keep.
        """
        if subdirectory not in self.process_paths:
            logger.warning(f"Invalid subdirectory for cleanup: {subdirectory}")
            return

        directory_path = self.process_paths[subdirectory]
        if not os.path.exists(directory_path):
            return

        for file in os.listdir(directory_path):
            file_path = os.path.join(directory_path, file)
            if os.path.isfile(file_path):
                should_keep = False
                if keep_patterns:
                    for pattern in keep_patterns:
                        if pattern in file:
                            should_keep = True
                            break

                if not should_keep:
                    try:
                        os.remove(file_path)
                        logger.info(f"Cleaned up PVC file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove {file_path}: {e}")


def get_pvc_manager(process_name: str = "misc_function") -> PVCDataManager:
    """Get a PVC data manager instance for a specific process.

    Args:
        process_name: Name of the process/DAG for namespace isolation.

    Returns:
        Configured manager instance.
    """
    return PVCDataManager(process_name)


def setup_local_testing_environment(
    process_name: str = "misc_function", sample_data_path: str | None = None
) -> None:
    """Set up local testing environment by creating sample data structure.

    Args:
        process_name: Name of the process/DAG for namespace isolation.
        sample_data_path: Path to existing data to copy for testing.
    """
    manager = get_pvc_manager(process_name)

    if manager.is_local:
        logger.info("Setting up local testing environment...")

        env_info = manager.get_environment_info()
        logger.info(f"Environment: {env_info}")

        if sample_data_path and os.path.exists(sample_data_path):
            import shutil

            try:
                for root, _, files in os.walk(sample_data_path):
                    for file in files:
                        if file.endswith((".parquet", ".pkl", ".json")):
                            src = os.path.join(root, file)
                            if "model" in file.lower() or file.endswith(".pkl"):
                                target_dir = "models"
                            elif "mapping" in file.lower() or "woe" in file.lower():
                                target_dir = "mapping"
                            else:
                                target_dir = "temp"

                            dest = manager.get_pvc_path(target_dir, file)
                            shutil.copy2(src, dest)
                            logger.info(f"Copied sample file: {file} -> {target_dir}/")
            except Exception as e:
                logger.warning(f"Failed to copy sample data: {e}")

        logger.info("Local testing environment ready!")
        logger.info(f"Shared data folder: {manager.base_path}")
        logger.info(
            "You can now run your processes locally and they will use the shared-data folder instead of OSS"
        )
    else:
        logger.info("Running in Kubernetes environment, no local setup needed")


if __name__ == "__main__":
    init_logging("pvc_data_manager_test")
    # Quick test/setup when running this file directly
    setup_local_testing_environment("misc_function")
