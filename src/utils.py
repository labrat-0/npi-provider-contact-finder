"""HTTP utilities and helpers for NPI Healthcare Provider Scraper."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# NPPES NPI Registry API v2.1
NPPES_API_URL = "https://npiregistry.cms.hhs.gov/api/"
NPPES_API_VERSION = "2.1"
NPPES_MAX_PER_PAGE = 200  # API max limit per request

DEFAULT_REQUEST_INTERVAL = 0.5
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 5


class RateLimiter:
    """Simple rate limiter that enforces a minimum interval between requests."""

    def __init__(self, interval: float = DEFAULT_REQUEST_INTERVAL) -> None:
        self._interval = interval
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request
            if elapsed < self._interval:
                await asyncio.sleep(self._interval - elapsed)
            self._last_request = asyncio.get_event_loop().time()


def build_headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": "Apify-NPI-Provider-Scraper/1.0",
    }


async def fetch_json(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any],
    rate_limiter: RateLimiter,
    headers: dict[str, str],
    max_retries: int = DEFAULT_MAX_RETRIES,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any] | None:
    """HTTP GET returning JSON with retries/backoff."""
    for attempt in range(max_retries + 1):
        await rate_limiter.wait()
        try:
            response = await client.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
            )

            status = response.status_code
            if status == 200:
                data = response.json()
                # NPPES API returns errors in the response body
                if "Errors" in data:
                    errors = data["Errors"]
                    logger.warning(
                        f"NPPES API error: {errors}"
                    )
                    return None
                return data

            if status in {429, 503, 502, 500}:
                delay = min(15.0, 1.5 * (2**attempt))
                jitter = random.uniform(0, 0.5)
                total = delay + jitter
                logger.warning(
                    f"{status} on NPPES API attempt {attempt+1}/{max_retries}. "
                    f"Retrying in {total:.1f}s"
                )
                await asyncio.sleep(total)
                continue

            if status == 404:
                logger.info(f"404 Not Found: {url}")
                return None

            logger.warning(
                f"Unexpected status {status} on NPPES API. Body: {response.text[:300]}"
            )
            return None

        except httpx.TimeoutException:
            delay = min(20.0, 2.0 * (attempt + 1))
            logger.warning(
                f"Timeout on NPPES API attempt {attempt+1}/{max_retries}. "
                f"Retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)
            continue
        except httpx.HTTPError as e:
            delay = min(20.0, 2.0 * (attempt + 1))
            logger.warning(
                f"HTTP error on NPPES API: {e}. attempt {attempt+1}/{max_retries}. "
                f"Retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)
            continue

    logger.error(f"All retries exhausted for NPPES API")
    return None
