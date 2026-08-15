"""
Live web evidence sourcing for manufacturer/brand resolution.

Provides a pluggable fetcher interface so different web/API providers
can be added later. The implementation is fully mockable so the test
suite never requires live network access.

Security & reliability:
- Requests use configurable timeouts (default 5s)
- Rate limiting via a simple per-provider delay
- Network failures are caught and logged, never raised
- No unrestricted crawling; providers must be explicitly registered
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from pipeline.reference_data import ReferenceData
from pipeline.schemas import Evidence, EvidenceType

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5
DEFAULT_DELAY = 0.5


@dataclass
class WebEvidenceResult:
    """A single piece of web-sourced evidence."""
    manufacturer: str
    brand: str | None
    source_url: str
    confidence: float
    signal: str


class WebEvidenceFetcher(ABC):
    """Abstract base class for web evidence providers.

    Subclass this to add a new provider (e.g. manufacturer website
    scraper, product-data API, etc.).  Implement ``fetch`` to return
    a list of ``WebEvidenceResult`` objects.
    """

    @abstractmethod
    def fetch(self, manufacturer_input: str | None, mpn: str | None, description: str | None) -> list[WebEvidenceResult]:
        """Fetch evidence from the web for the given product signals.

        Parameters
        ----------
        manufacturer_input : str or None
            The raw manufacturer string from the input catalog.
        mpn : str or None
            The manufacturer part number.
        description : str or None
            The product description.

        Returns
        -------
        list[WebEvidenceResult]
            Evidence found from this provider.  Empty list if nothing found.
        """
        ...


class WebEvidenceProvider:
    """Orchestrates evidence gathering from all registered fetchers.

    Usage::

        provider = WebEvidenceProvider()
        provider.register(DummyFetcher())
        results = provider.gather("Moen", "MN-7000", "Kitchen faucet")
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT, delay: float = DEFAULT_DELAY):
        self._fetchers: list[WebEvidenceFetcher] = []
        self.timeout = timeout
        self.delay = delay

    def register(self, fetcher: WebEvidenceFetcher) -> None:
        """Register a web evidence fetcher."""
        self._fetchers.append(fetcher)

    @property
    def enabled(self) -> bool:
        """True if at least one fetcher is registered."""
        return len(self._fetchers) > 0

    def gather(
        self,
        manufacturer_input: str | None,
        mpn: str | None,
        description: str | None,
    ) -> list[WebEvidenceResult]:
        """Gather evidence from all registered fetchers.

        Failures in individual fetchers are logged and skipped, never raised.
        A small delay between providers avoids hammering upstream services.
        """
        all_results: list[WebEvidenceResult] = []
        for i, fetcher in enumerate(self._fetchers):
            try:
                results = fetcher.fetch(manufacturer_input, mpn, description)
                all_results.extend(results)
            except Exception:
                logger.warning("Web evidence fetcher %s failed", type(fetcher).__name__, exc_info=True)
            if i < len(self._fetchers) - 1:
                time.sleep(self.delay)
        return all_results

    def to_evidence(self, results: list[WebEvidenceResult]) -> list[Evidence]:
        """Convert WebEvidenceResult objects into Evidence objects for the pipeline."""
        evidence = []
        for r in results:
            evidence.append(Evidence(
                type=EvidenceType.WEB_SOURCED,
                signal=f"Web-sourced evidence from {r.source_url}: {r.signal}",
                value=r.manufacturer,
                strength=r.confidence,
            ))
        return evidence


class DummyFetcher(WebEvidenceFetcher):
    """A no-op fetcher for testing and demonstration.

    Always returns an empty list.  Useful for verifying the provider
    interface works without network calls.
    """

    def fetch(self, manufacturer_input: str | None, mpn: str | None, description: str | None) -> list[WebEvidenceResult]:
        return []
