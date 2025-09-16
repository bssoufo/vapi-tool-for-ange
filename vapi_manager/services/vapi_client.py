import httpx
from typing import List, Dict, Any, Optional
from ..config.settings import settings
from ..core.exceptions.vapi_exceptions import VAPIAPIError


class VAPIClient:
    """HTTP client for VAPI API interactions."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.vapi_api_key
        self.base_url = base_url or settings.vapi_base_url
        self.timeout = settings.timeout

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to VAPI API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    params=params
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                raise VAPIAPIError(
                    message=f"VAPI API error: {e.response.text}",
                    status_code=e.response.status_code,
                    response_body=e.response.text
                ) from e

            except httpx.RequestError as e:
                raise VAPIAPIError(f"Request failed: {str(e)}") from e

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request."""
        return await self._make_request("GET", endpoint, params=params)

    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request."""
        return await self._make_request("POST", endpoint, data=data)

    async def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make PUT request."""
        return await self._make_request("PUT", endpoint, data=data)

    async def patch(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make PATCH request."""
        return await self._make_request("PATCH", endpoint, data=data)

    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request."""
        return await self._make_request("DELETE", endpoint)