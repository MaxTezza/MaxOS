"""Google Analytics telemetry integration for MaxOS."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)


class GoogleAnalytics:
    """Google Analytics 4 Measurement Protocol client."""

    def __init__(self, measurement_id: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize Google Analytics client.

        Args:
            measurement_id: GA4 Measurement ID (e.g., G-XXXXXXXXXX)
            api_secret: Measurement Protocol API Secret
        """
        self.measurement_id = measurement_id or os.environ.get("GA_MEASUREMENT_ID")
        self.api_secret = api_secret or os.environ.get("GA_API_SECRET")
        self.endpoint = "https://www.google-analytics.com/mp/collect"
        self.enabled = bool(self.measurement_id and self.api_secret)

    async def send_event(
        self,
        event_name: str,
        client_id: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send an event to Google Analytics.

        Args:
            event_name: Name of the event (e.g., 'agent_execution', 'intent_parsed')
            client_id: Unique client identifier
            params: Additional event parameters

        Returns:
            True if event was sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        if params is None:
            params = {}

        payload = {
            "client_id": client_id,
            "events": [
                {
                    "name": event_name,
                    "params": params,
                }
            ],
        }

        url = f"{self.endpoint}?{urlencode({'measurement_id': self.measurement_id, 'api_secret': self.api_secret})}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 204
        except Exception as e:
            # Silently fail - telemetry should not break the app
            logger.debug(f"GA telemetry error: {e}")
            return False

    async def send_page_view(self, client_id: str, page_path: str, page_title: Optional[str] = None) -> bool:
        """
        Send a page view event.

        Args:
            client_id: Unique client identifier
            page_path: Path of the page
            page_title: Optional title of the page

        Returns:
            True if event was sent successfully, False otherwise
        """
        params = {"page_path": page_path}
        if page_title:
            params["page_title"] = page_title

        return await self.send_event("page_view", client_id, params)

    async def send_agent_execution(
        self,
        client_id: str,
        agent_name: str,
        success: bool,
        duration_ms: Optional[int] = None,
    ) -> bool:
        """
        Send an agent execution event.

        Args:
            client_id: Unique client identifier
            agent_name: Name of the agent that was executed
            success: Whether the execution was successful
            duration_ms: Optional duration in milliseconds

        Returns:
            True if event was sent successfully, False otherwise
        """
        params = {
            "agent_name": agent_name,
            "success": success,
        }
        if duration_ms is not None:
            params["duration_ms"] = duration_ms

        return await self.send_event("agent_execution", client_id, params)


# Singleton instance
_ga_instance: Optional[GoogleAnalytics] = None


def get_ga_client(settings: Optional[Dict[str, Any]] = None) -> GoogleAnalytics:
    """
    Get or create the Google Analytics client singleton.

    Args:
        settings: Optional telemetry settings dict

    Returns:
        GoogleAnalytics instance
    """
    global _ga_instance
    if _ga_instance is None:
        measurement_id = None
        api_secret = None

        if settings and "google_analytics" in settings:
            ga_config = settings["google_analytics"]
            measurement_id = ga_config.get("measurement_id")
            api_secret = ga_config.get("api_secret")

        _ga_instance = GoogleAnalytics(measurement_id=measurement_id, api_secret=api_secret)

    return _ga_instance
