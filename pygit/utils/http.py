"""
HTTP utilities module.

This module provides reusable HTTP operations for file downloads,
API requests, and network operations.
"""

import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Union, Callable
from .logging import get_logger


class HTTPClient:
    """HTTP client for downloading files and making requests."""

    def __init__(self, progress_callback: Optional[Callable[[int, int], None]] = None):
        self.progress_callback = progress_callback
        self.logger = get_logger()

    def download_file(
        self, url: str, destination: Union[str, Path], create_dirs: bool = True
    ) -> bool:
        """Download a file from URL to destination."""
        destination = Path(destination)

        if create_dirs:
            destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            with urllib.request.urlopen(url) as response:
                # Get file size for progress tracking
                content_length = response.getheader("Content-Length")
                total_size = int(content_length) if content_length else None

                downloaded = 0
                chunk_size = 8192

                with destination.open("wb") as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        if self.progress_callback and total_size:
                            self.progress_callback(downloaded, total_size)

            self.logger.debug(f"Successfully downloaded {url} to {destination}")
            return True

        except urllib.error.HTTPError as e:
            if e.code != 404:
                self.logger.error(f"HTTP Error {e.code} downloading {url}: {e.reason}")
            return False
        except Exception as e:
            self.logger.error(f"Error downloading {url}: {e}")
            return False

    def download_with_retry(
        self,
        url: str,
        destination: Union[str, Path],
        max_retries: int = 3,
        create_dirs: bool = True,
    ) -> bool:
        """Download a file with retry logic."""
        for attempt in range(max_retries):
            if self.download_file(url, destination, create_dirs):
                return True

            if attempt < max_retries - 1:
                wait_time = 2**attempt  # Exponential backoff
                self.logger.info(
                    f"Retrying download in {wait_time}s (attempt {attempt + 2}/{max_retries})"
                )
                import time

                time.sleep(wait_time)

        self.logger.error(f"Failed to download {url} after {max_retries} attempts")
        return False

    def make_request(self, url: str, headers: Optional[dict] = None) -> Optional[bytes]:
        """Make a simple HTTP GET request."""
        try:
            req = urllib.request.Request(url)

            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)

            with urllib.request.urlopen(req) as response:
                return response.read()

        except urllib.error.HTTPError as e:
            self.logger.error(f"HTTP Error {e.code} for {url}: {e.reason}")
            return None
        except Exception as e:
            self.logger.error(f"Error making request to {url}: {e}")
            return None


def download_file_with_progress(
    url: str, destination: Union[str, Path], description: str = "Downloading"
) -> bool:
    """Convenience function to download a file with progress display."""

    def progress_callback(downloaded: int, total: int):
        percentage = (downloaded / total) * 100
        logger = get_logger()
        logger.progress(
            f"{description}: {downloaded:,}/{total:,} bytes ({percentage:.1f}%)",
            downloaded,
            total,
        )

    client = HTTPClient(progress_callback)
    return client.download_with_retry(url, destination)


def is_url_accessible(url: str) -> bool:
    """Check if a URL is accessible."""
    try:
        urllib.request.urlopen(url)
        return True
    except:
        return False
