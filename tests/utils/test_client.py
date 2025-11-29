"""
Test client wrapper cho Robyn app.

Wrapper này giúp test API endpoints dễ dàng hơn.
Sử dụng httpx để test async endpoints của Robyn.
"""

from __future__ import annotations

import json
from typing import Any

from robyn import Response


class APIClient:
    """Wrapper để test API endpoints dễ dàng hơn.
    
    Sử dụng httpx AsyncClient hoặc có thể dùng Robyn's built-in test client.
    """
    
    def __init__(self, app):
        """Khởi tạo API client với Robyn app."""
        self.app = app
        # Sử dụng httpx để test async app
        try:
            from httpx import AsyncClient, ASGITransport
            # Robyn có thể test như ASGI app
            transport = ASGITransport(app=app)  # type: ignore
            self._client = AsyncClient(transport=transport, base_url="http://test")
            self._is_async = True
        except (ImportError, Exception):
            # Fallback: Dùng sync client hoặc skip tests
            try:
                import httpx
                self._client = httpx.Client(base_url="http://localhost:8000")
                self._is_async = False
            except ImportError:
                raise ImportError("httpx is required for testing. Install with: pip install httpx")
    
    def _sync_request(self, method: str, path: str, **kwargs):
        """Sync request helper."""
        import asyncio
        
        if self._is_async:
            try:
                # Try to get running event loop
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            coro = getattr(self._client, method.lower())(path, **kwargs)
            response = loop.run_until_complete(coro)
        else:
            response = getattr(self._client, method.lower())(path, **kwargs)
        
        # Convert httpx response to Robyn Response-like object
        return Response(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.content
        )
    
    def get(self, path: str, **kwargs) -> Response:
        """GET request."""
        return self._sync_request("get", path, **kwargs)
    
    def post(self, path: str, json: dict | None = None, **kwargs) -> Response:
        """POST request với JSON body."""
        if json is not None:
            kwargs["json"] = json
        return self._sync_request("post", path, **kwargs)
    
    def put(self, path: str, json: dict | None = None, **kwargs) -> Response:
        """PUT request với JSON body."""
        if json is not None:
            kwargs["json"] = json
        return self._sync_request("put", path, **kwargs)
    
    def delete(self, path: str, **kwargs) -> Response:
        """DELETE request."""
        return self._sync_request("delete", path, **kwargs)
    
    def json_response(self, response: Response) -> dict[str, Any]:
        """Parse JSON response body."""
        if response.body is None:
            return {}
        
        if isinstance(response.body, bytes):
            body_str = response.body.decode("utf-8")
        else:
            body_str = str(response.body)
        
        try:
            return json.loads(body_str)
        except json.JSONDecodeError:
            return {"raw": body_str}
