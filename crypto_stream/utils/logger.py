import logging
from pathlib import Path
from typing import Optional
from datetime import datetime


class LoggerSetup:
    """Utility class for setting up logging across the application."""

    # Get the crypto_stream directory path
    PACKAGE_ROOT = Path(__file__).parent.parent
    LOG_DIR = PACKAGE_ROOT / ".logs"

    @classmethod
    def setup_logger(
        cls,
        name: str,
        level: int = logging.INFO,
        log_format: Optional[str] = None,
        date_format: Optional[str] = None,
    ) -> logging.Logger:
        """
        Set up and return a logger instance with the specified configuration.

        Args:
            name: Name of the logger
            level: Logging level (default: logging.INFO)
            log_format: Custom log format string (optional)
            date_format: Custom date format string (optional)

        Returns:
            logging.Logger: Configured logger instance
        """
        logger = logging.getLogger(name)

        if not logger.handlers:  # Only add handler if none exists
            logger.setLevel(level)

            # Default formats if none provided
            if log_format is None:
                log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            if date_format is None:
                date_format = "%Y-%m-%d %H:%M:%S"

            # Create formatter
            formatter = logging.Formatter(log_format, date_format)

            # Create and configure console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            # Create and configure file handler
            cls.LOG_DIR.mkdir(exist_ok=True)
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = cls.LOG_DIR / f"{name.replace('.', '_')}_{current_time}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger
