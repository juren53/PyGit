"""
Unit tests for pygit.utils.http module.

Tests for HTTPClient class including download, retry logic,
and request handling.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO

import pytest

from pygit.utils.http import HTTPClient, download_file_with_progress, is_url_accessible


class TestHTTPClient:
    """Tests for HTTPClient class."""

    @pytest.mark.unit
    def test_client_creation(self):
        """Test creating HTTP client."""
        client = HTTPClient()
        assert client.progress_callback is None

    @pytest.mark.unit
    def test_client_with_progress_callback(self):
        """Test creating client with progress callback."""
        callback = MagicMock()
        client = HTTPClient(progress_callback=callback)
        assert client.progress_callback == callback


class TestHTTPClientDownload:
    """Tests for download functionality."""

    @pytest.mark.unit
    def test_download_file_success(self, temp_dir):
        """Test successful file download."""
        client = HTTPClient()
        dest_file = temp_dir / "downloaded.txt"

        # Mock the urlopen
        mock_response = MagicMock()
        mock_response.read.side_effect = [b"test content", b""]
        mock_response.getheader.return_value = None
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = client.download_file(
                "https://example.com/file.txt",
                dest_file
            )

        assert result is True
        assert dest_file.exists()

    @pytest.mark.unit
    def test_download_file_creates_dirs(self, temp_dir):
        """Test that download creates parent directories."""
        client = HTTPClient()
        dest_file = temp_dir / "subdir" / "nested" / "file.txt"

        mock_response = MagicMock()
        mock_response.read.side_effect = [b"content", b""]
        mock_response.getheader.return_value = None
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = client.download_file(
                "https://example.com/file.txt",
                dest_file,
                create_dirs=True
            )

        assert result is True
        assert dest_file.parent.exists()

    @pytest.mark.unit
    def test_download_file_http_error(self, temp_dir):
        """Test handling of HTTP errors."""
        client = HTTPClient()
        dest_file = temp_dir / "file.txt"

        import urllib.error
        error = urllib.error.HTTPError(
            "https://example.com/file.txt",
            500,
            "Server Error",
            {},
            None
        )

        with patch("urllib.request.urlopen", side_effect=error):
            result = client.download_file(
                "https://example.com/file.txt",
                dest_file
            )

        assert result is False

    @pytest.mark.unit
    def test_download_file_404_silent(self, temp_dir):
        """Test that 404 errors are handled silently."""
        client = HTTPClient()
        dest_file = temp_dir / "file.txt"

        import urllib.error
        error = urllib.error.HTTPError(
            "https://example.com/file.txt",
            404,
            "Not Found",
            {},
            None
        )

        with patch("urllib.request.urlopen", side_effect=error):
            result = client.download_file(
                "https://example.com/file.txt",
                dest_file
            )

        assert result is False

    @pytest.mark.unit
    def test_download_with_progress(self, temp_dir):
        """Test download with progress callback."""
        progress_calls = []

        def progress_callback(downloaded, total):
            progress_calls.append((downloaded, total))

        client = HTTPClient(progress_callback=progress_callback)
        dest_file = temp_dir / "file.txt"

        mock_response = MagicMock()
        mock_response.read.side_effect = [b"a" * 100, b"b" * 100, b""]
        mock_response.getheader.return_value = "200"  # Content-Length
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            client.download_file(
                "https://example.com/file.txt",
                dest_file
            )

        # Progress should have been called
        assert len(progress_calls) > 0


class TestHTTPClientRetry:
    """Tests for retry functionality."""

    @pytest.mark.unit
    def test_download_with_retry_success_first_try(self, temp_dir):
        """Test retry succeeds on first attempt."""
        client = HTTPClient()
        dest_file = temp_dir / "file.txt"

        mock_response = MagicMock()
        mock_response.read.side_effect = [b"content", b""]
        mock_response.getheader.return_value = None
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = client.download_with_retry(
                "https://example.com/file.txt",
                dest_file,
                max_retries=3
            )

        assert result is True

    @pytest.mark.unit
    def test_download_with_retry_eventual_success(self, temp_dir):
        """Test retry succeeds after initial failures."""
        client = HTTPClient()
        dest_file = temp_dir / "file.txt"

        import urllib.error

        # First two calls fail, third succeeds
        mock_response = MagicMock()
        mock_response.read.side_effect = [b"content", b""]
        mock_response.getheader.return_value = None
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        error = urllib.error.HTTPError(
            "url", 500, "Error", {}, None
        )

        call_count = [0]
        def mock_urlopen(url):
            call_count[0] += 1
            if call_count[0] < 3:
                raise error
            return mock_response

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            with patch("time.sleep"):  # Skip actual sleep
                result = client.download_with_retry(
                    "https://example.com/file.txt",
                    dest_file,
                    max_retries=3
                )

        assert result is True

    @pytest.mark.unit
    def test_download_with_retry_all_fail(self, temp_dir):
        """Test retry exhausts all attempts."""
        client = HTTPClient()
        dest_file = temp_dir / "file.txt"

        import urllib.error
        error = urllib.error.HTTPError(
            "url", 500, "Error", {}, None
        )

        with patch("urllib.request.urlopen", side_effect=error):
            with patch("time.sleep"):  # Skip actual sleep
                result = client.download_with_retry(
                    "https://example.com/file.txt",
                    dest_file,
                    max_retries=3
                )

        assert result is False


class TestHTTPClientRequest:
    """Tests for make_request functionality."""

    @pytest.mark.unit
    def test_make_request_success(self):
        """Test successful request."""
        client = HTTPClient()

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"key": "value"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = client.make_request("https://example.com/api")

        assert result == b'{"key": "value"}'

    @pytest.mark.unit
    def test_make_request_with_headers(self):
        """Test request with custom headers."""
        client = HTTPClient()

        mock_response = MagicMock()
        mock_response.read.return_value = b"response"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
            with patch("urllib.request.Request") as mock_request_class:
                mock_request = MagicMock()
                mock_request_class.return_value = mock_request

                client.make_request(
                    "https://example.com/api",
                    headers={"Authorization": "Bearer token"}
                )

                mock_request.add_header.assert_called_with(
                    "Authorization", "Bearer token"
                )

    @pytest.mark.unit
    def test_make_request_error(self):
        """Test request error handling."""
        client = HTTPClient()

        import urllib.error
        error = urllib.error.HTTPError(
            "url", 401, "Unauthorized", {}, None
        )

        with patch("urllib.request.urlopen", side_effect=error):
            result = client.make_request("https://example.com/api")

        assert result is None


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.mark.unit
    def test_is_url_accessible_true(self):
        """Test URL accessibility check returns true."""
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = is_url_accessible("https://example.com")

        assert result is True

    @pytest.mark.unit
    def test_is_url_accessible_false(self):
        """Test URL accessibility check returns false."""
        with patch("urllib.request.urlopen", side_effect=Exception("Error")):
            result = is_url_accessible("https://example.com")

        assert result is False
