"""HTTP connection pool management for AIOps.

This module provides efficient HTTP connection pooling for external service calls,
reducing overhead and improving performance.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector

from aiops.config.settings import load_settings

logger = logging.getLogger(__name__)


class HTTPConnectionPool:
    """HTTP connection pool manager.

    Manages connection pools for different services, allowing for efficient
    reuse of connections and proper resource cleanup.

    Example:
        ```python
        pool = HTTPConnectionPool()

        async with pool.get_session("prometheus") as session:
            async with session.get("http://prometheus:9090/api/v1/query") as resp:
                data = await resp.json()
        ```

    Args:
        timeout: Default request timeout in seconds
        limit_per_host: Maximum connections per host
        total_limit: Maximum total connections
    """

    def __init__(
        self,
        timeout: int = 30,
        limit_per_host: int = 10,
        total_limit: int = 100,
    ):
        """Initialize the connection pool manager.

        Args:
            timeout: Default request timeout in seconds
            limit_per_host: Maximum connections per host
            total_limit: Maximum total connections across all hosts
        """
        self.timeout = timeout
        self.limit_per_host = limit_per_host
        self.total_limit = total_limit
        self._pools: Dict[str, ClientSession] = {}
        self._lock = asyncio.Lock()

    async def get_session(
        self,
        service: str,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> ClientSession:
        """Get or create a connection session for a service.

        Args:
            service: Service identifier (e.g., "prometheus", "victorialogs")
            base_url: Optional base URL for the service
            timeout: Optional timeout override

        Returns:
            A ClientSession for making HTTP requests
        """
        async with self._lock:
            if service not in self._pools:
                # Create timeout
                request_timeout = ClientTimeout(
                    total=timeout or self.timeout
                )

                # Create connector with limits
                connector = TCPConnector(
                    limit=self.total_limit,
                    limit_per_host=self.limit_per_host,
                    ttl_dns_cache=300,  # Cache DNS for 5 minutes
                )

                # Create session
                self._pools[service] = ClientSession(
                    timeout=request_timeout,
                    connector=connector,
                    raise_for_status=False,
                )

                logger.debug(
                    f"Created HTTP session for {service} "
                    f"(limit_per_host={self.limit_per_host}, total_limit={self.total_limit})"
                )

            return self._pools[service]

    @asynccontextmanager
    async def session(
        self,
        service: str,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> AsyncIterator[ClientSession]:
        """Context manager for getting a session.

        Args:
            service: Service identifier
            base_url: Optional base URL for the service
            timeout: Optional timeout override

        Yields:
            A ClientSession for making HTTP requests
        """
        session = await self.get_session(service, base_url, timeout)
        try:
            yield session
        except Exception as e:
            logger.error(f"HTTP error for {service}: {e}")
            raise

    async def close(self, service: Optional[str] = None) -> None:
        """Close connection sessions.

        Args:
            service: Specific service to close, or None to close all
        """
        async with self._lock:
            if service:
                if service in self._pools:
                    await self._pools[service].close()
                    del self._pools[service]
                    logger.debug(f"Closed HTTP session for {service}")
            else:
                for svc, session in self._pools.items():
                    await session.close()
                    logger.debug(f"Closed HTTP session for {svc}")
                self._pools.clear()

    async def get_stats(self) -> Dict[str, Dict]:
        """Get connection pool statistics.

        Returns:
            Dictionary with stats for each service pool
        """
        stats = {}
        for service, session in self._pools.items():
            connector = session.connector
            if connector:
                stats[service] = {
                    "total_connections": connector.limit,
                    "active_connections": len(connector._acquired),
                    "limit_per_host": connector.limit_per_host,
                }
        return stats


class ServiceHTTPClient:
    """High-level HTTP client for external services.

    Provides convenient methods for making HTTP requests to configured services.

    Example:
        ```python
        client = ServiceHTTPClient()

        # GET request
        data = await client.get("prometheus", "/api/v1/query", params={"query": "up"})

        # POST request
        result = await client.post("victorialogs", "/query", json={"query": "..."})

        # Close when done
        await client.close()
        ```
    """

    def __init__(
        self,
        pool: Optional[HTTPConnectionPool] = None,
        settings: Optional[Any] = None,
    ):
        """Initialize the service HTTP client.

        Args:
            pool: Optional connection pool to use
            settings: Optional settings object
        """
        self.pool = pool or HTTPConnectionPool()
        self.settings = settings or load_settings()

        # Service base URLs from settings
        self._base_urls = {
            "prometheus": getattr(
                self.settings.metrics, "prometheus_base_url", None
            ) if hasattr(self.settings, "metrics") else None,
            "victorialogs": getattr(
                self.settings.logs, "victorialogs_base_url", None
            ) if hasattr(self.settings, "logs") else None,
            "chromadb": getattr(
                self.settings.knowledge, "chroma_persist_directory", None
            ) if hasattr(self.settings, "knowledge") else None,
        }

    async def get(
        self,
        service: str,
        path: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
    ) -> Dict:
        """Make a GET request to a service.

        Args:
            service: Service name
            path: Request path
            params: Query parameters
            headers: Request headers
            timeout: Request timeout override

        Returns:
            Response data as dictionary
        """
        base_url = self._base_urls.get(service)
        if not base_url:
            raise ValueError(f"No base URL configured for service: {service}")

        url = f"{base_url}{path}"

        async with self.pool.session(service) as session:
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
            ) as response:
                return await self._handle_response(response)

    async def post(
        self,
        service: str,
        path: str,
        json: Optional[Dict] = None,
        data: Optional[str] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
    ) -> Dict:
        """Make a POST request to a service.

        Args:
            service: Service name
            path: Request path
            json: JSON body
            data: Raw body data
            headers: Request headers
            timeout: Request timeout override

        Returns:
            Response data as dictionary
        """
        base_url = self._base_urls.get(service)
        if not base_url:
            raise ValueError(f"No base URL configured for service: {service}")

        url = f"{base_url}{path}"

        async with self.pool.session(service) as session:
            async with session.post(
                url,
                json=json,
                data=data,
                headers=headers,
                timeout=timeout,
            ) as response:
                return await self._handle_response(response)

    async def put(
        self,
        service: str,
        path: str,
        json: Optional[Dict] = None,
        data: Optional[str] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
    ) -> Dict:
        """Make a PUT request to a service.

        Args:
            service: Service name
            path: Request path
            json: JSON body
            data: Raw body data
            headers: Request headers
            timeout: Request timeout override

        Returns:
            Response data as dictionary
        """
        base_url = self._base_urls.get(service)
        if not base_url:
            raise ValueError(f"No base URL configured for service: {service}")

        url = f"{base_url}{path}"

        async with self.pool.session(service) as session:
            async with session.put(
                url,
                json=json,
                data=data,
                headers=headers,
                timeout=timeout,
            ) as response:
                return await self._handle_response(response)

    async def delete(
        self,
        service: str,
        path: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
    ) -> Dict:
        """Make a DELETE request to a service.

        Args:
            service: Service name
            path: Request path
            params: Query parameters
            headers: Request headers
            timeout: Request timeout override

        Returns:
            Response data as dictionary
        """
        base_url = self._base_urls.get(service)
        if not base_url:
            raise ValueError(f"No base URL configured for service: {service}")

        url = f"{base_url}{path}"

        async with self.pool.session(service) as session:
            async with session.delete(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
            ) as response:
                return await self._handle_response(response)

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict:
        """Handle HTTP response.

        Args:
            response: The aiohttp response object

        Returns:
            Response data as dictionary

        Raises:
            aiohttp.ClientResponseError: If response indicates an error
        """
        # Check for HTTP errors
        if response.status >= 400:
            error_data = None
            try:
                error_data = await response.json()
            except Exception:
                error_data = await response.text()

            raise aiohttp.ClientResponseError(
                request_info=response.request_info,
                history=response.history,
                status=response.status,
                message=error_data or f"HTTP {response.status}",
            )

        # Try to parse as JSON
        try:
            return await response.json()
        except aiohttp.ContentTypeError:
            # Return text content if not JSON
            text = await response.text()
            return {"data": text, "content_type": response.content_type}

    async def close(self) -> None:
        """Close all connection sessions."""
        await self.pool.close()


# Global HTTP client instance
_global_client: Optional[ServiceHTTPClient] = None


def get_http_client() -> ServiceHTTPClient:
    """Get the global HTTP client instance.

    Returns:
        The global HTTP client
    """
    global _global_client
    if _global_client is None:
        _global_client = ServiceHTTPClient()
    return _global_client


async def close_http_client() -> None:
    """Close the global HTTP client.

    Should be called when shutting down the application.
    """
    global _global_client
    if _global_client is not None:
        await _global_client.close()
        _global_client = None
