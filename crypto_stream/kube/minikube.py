import subprocess
from typing import Dict, Optional
import json

from crypto_stream.utils.logger import LoggerSetup

logger = LoggerSetup.setup_logger(__name__)


class MinikubeManager:
    """A class to manage Minikube cluster operations."""

    def __init__(self, memory: str = "4096", cpus: int = 2, driver: str = "docker"):
        """
        Initialize MinikubeManager with cluster configuration.

        Args:
            memory: Memory allocation for Minikube (in MB)
            cpus: Number of CPUs to allocate
            driver: VM driver to use (docker, virtualbox, etc.)
        """
        self.memory = memory
        self.cpus = cpus
        self.driver = driver

    def _run_command(self, command: list) -> subprocess.CompletedProcess:
        """Execute a shell command and return the result."""
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(command)}")
            logger.error(f"Error output: {e.stderr}")
            raise

    def start_cluster(self) -> bool:
        """
        Start the Minikube cluster with specified configuration.

        Returns:
            bool: True if cluster started successfully
        """
        command = [
            "minikube",
            "start",
            f"--memory={self.memory}",
            f"--cpus={self.cpus}",
            f"--driver={self.driver}",
        ]

        try:
            self._run_command(command)
            logger.info("Minikube cluster started successfully")
            return True
        except subprocess.CalledProcessError:
            logger.error("Failed to start Minikube cluster")
            return False

    def stop_cluster(self) -> bool:
        """
        Stop the Minikube cluster.

        Returns:
            bool: True if cluster stopped successfully
        """
        try:
            self._run_command(["minikube", "stop"])
            logger.info("Minikube cluster stopped successfully")
            return True
        except subprocess.CalledProcessError:
            logger.error("Failed to stop Minikube cluster")
            return False

    def delete_cluster(self) -> bool:
        """
        Delete the Minikube cluster.

        Returns:
            bool: True if cluster deleted successfully
        """
        try:
            self._run_command(["minikube", "delete"])
            logger.info("Minikube cluster deleted successfully")
            return True
        except subprocess.CalledProcessError:
            logger.error("Failed to delete Minikube cluster")
            return False

    def get_cluster_status(self) -> Optional[Dict]:
        """
        Get the current status of the Minikube cluster.

        Returns:
            Dict: Cluster status information or None if failed
        """
        try:
            result = self._run_command(["minikube", "status", "-o", "json"])
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            logger.error("Failed to get cluster status")
            return None

    def enable_addon(self, addon_name: str) -> bool:
        """
        Enable a Minikube addon.

        Args:
            addon_name: Name of the addon to enable

        Returns:
            bool: True if addon enabled successfully
        """
        try:
            self._run_command(["minikube", "addons", "enable", addon_name])
            logger.info(f"Addon {addon_name} enabled successfully")
            return True
        except subprocess.CalledProcessError:
            logger.error(f"Failed to enable addon {addon_name}")
            return False
