"""
HTTP Mock Infrastructure

This module provides mock implementations for HTTP requests
to enable testing without network access.
"""

import json
from typing import Dict, Any, Optional, Union, Callable
from unittest.mock import MagicMock, patch
from contextlib import contextmanager
from io import BytesIO


class MockHTTPResponse:
    """Mock HTTP response object compatible with urllib.request.urlopen."""

    def __init__(
        self,
        data: Union[bytes, str, Dict[str, Any]],
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        url: str = "https://example.com",
    ):
        if isinstance(data, dict):
            self._data = json.dumps(data).encode("utf-8")
        elif isinstance(data, str):
            self._data = data.encode("utf-8")
        else:
            self._data = data

        self.status = status
        self.code = status  # Alias for compatibility
        self.reason = self._get_reason(status)
        self.headers = headers or {"Content-Type": "application/json"}
        self.url = url
        self._buffer = BytesIO(self._data)

    def _get_reason(self, status: int) -> str:
        """Get HTTP reason phrase for status code."""
        reasons = {
            200: "OK",
            201: "Created",
            204: "No Content",
            301: "Moved Permanently",
            302: "Found",
            304: "Not Modified",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            422: "Unprocessable Entity",
            429: "Too Many Requests",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
        }
        return reasons.get(status, "Unknown")

    def read(self, amt: Optional[int] = None) -> bytes:
        """Read response data."""
        if amt is None:
            return self._data
        return self._buffer.read(amt)

    def readline(self) -> bytes:
        """Read a line from response."""
        return self._buffer.readline()

    def readlines(self):
        """Read all lines from response."""
        return self._buffer.readlines()

    def getheader(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a response header."""
        return self.headers.get(name, default)

    def getheaders(self):
        """Get all response headers."""
        return list(self.headers.items())

    def info(self):
        """Return headers (for compatibility)."""
        return self.headers

    def geturl(self) -> str:
        """Return the URL."""
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockHTTPError(Exception):
    """Mock HTTP error for testing error handling."""

    def __init__(
        self,
        url: str,
        code: int,
        msg: str = "Error",
        hdrs: Optional[Dict] = None,
        fp: Optional[BytesIO] = None,
    ):
        self.url = url
        self.code = code
        self.msg = msg
        self.reason = msg
        self.hdrs = hdrs or {}
        self.fp = fp or BytesIO(b"")
        super().__init__(f"HTTP Error {code}: {msg}")

    def read(self) -> bytes:
        """Read error response body."""
        return self.fp.read()


class HTTPMockRouter:
    """Router for mock HTTP responses based on URL patterns."""

    def __init__(self):
        self.routes: Dict[str, Callable] = {}
        self.default_response: Optional[MockHTTPResponse] = None
        self.call_history: list = []

    def add_route(
        self,
        url_pattern: str,
        response: Union[MockHTTPResponse, Callable, Dict[str, Any], bytes],
        status: int = 200,
    ) -> None:
        """Add a route that matches a URL pattern.

        Args:
            url_pattern: URL or pattern to match (substring match)
            response: Response to return (MockHTTPResponse, callable, dict, or bytes)
            status: HTTP status code (used if response is dict/bytes)
        """
        if isinstance(response, (dict, bytes)):
            response = MockHTTPResponse(response, status=status, url=url_pattern)

        if isinstance(response, MockHTTPResponse):
            self.routes[url_pattern] = lambda req: response
        else:
            self.routes[url_pattern] = response

    def add_error(
        self,
        url_pattern: str,
        status: int,
        message: str = "Error",
    ) -> None:
        """Add a route that returns an HTTP error."""
        def error_handler(req):
            raise MockHTTPError(req.full_url, status, message)

        self.routes[url_pattern] = error_handler

    def set_default(
        self,
        response: Union[MockHTTPResponse, Dict[str, Any], bytes],
        status: int = 200,
    ) -> None:
        """Set default response for unmatched URLs."""
        if isinstance(response, (dict, bytes)):
            response = MockHTTPResponse(response, status=status)
        self.default_response = response

    def __call__(self, request) -> MockHTTPResponse:
        """Handle a mock request."""
        url = request.full_url if hasattr(request, "full_url") else str(request)
        self.call_history.append(url)

        # Find matching route
        for pattern, handler in self.routes.items():
            if pattern in url:
                return handler(request)

        # Return default or 404
        if self.default_response:
            return self.default_response

        raise MockHTTPError(url, 404, "Not Found")

    def reset(self) -> None:
        """Reset routes and history."""
        self.routes.clear()
        self.call_history.clear()
        self.default_response = None


# Global mock router instance for simple usage
_mock_router = HTTPMockRouter()


def mock_urlopen(request):
    """Drop-in replacement for urllib.request.urlopen."""
    return _mock_router(request)


@contextmanager
def mock_http(router: Optional[HTTPMockRouter] = None):
    """Context manager to mock HTTP requests.

    Usage:
        with mock_http() as router:
            router.add_route(
                "api.github.com/repos",
                {"name": "test-repo", "default_branch": "main"}
            )
            # ... test code that makes HTTP requests ...
    """
    if router is None:
        router = HTTPMockRouter()

    with patch("urllib.request.urlopen", router):
        yield router


@contextmanager
def mock_http_responses(responses: Dict[str, Union[Dict, bytes, MockHTTPResponse]]):
    """Convenience context manager for simple response mocking.

    Usage:
        with mock_http_responses({
            "api.github.com": {"name": "test"},
            "raw.githubusercontent.com": b"file content",
        }):
            # ... test code ...
    """
    router = HTTPMockRouter()
    for pattern, response in responses.items():
        router.add_route(pattern, response)

    with patch("urllib.request.urlopen", router):
        yield router
