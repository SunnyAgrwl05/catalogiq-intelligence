import unittest

from pipeline.enrichment import enrich_catalog, enrich_manufacturer_field
from pipeline.reference_data import load_reference_data
from pipeline.schemas import EvidenceType, ValidationState
from pipeline.web_evidence import DummyFetcher, WebEvidenceProvider, WebEvidenceResult


class MockFetcher(DummyFetcher):
    """A mock fetcher that returns predictable results for testing."""

    def __init__(self, results: list[WebEvidenceResult] | None = None):
        self._results = results or []
        self.call_count = 0
        self.last_args = None

    def fetch(self, manufacturer_input, mpn, description):
        self.call_count += 1
        self.last_args = (manufacturer_input, mpn, description)
        return self._results


class FailingFetcher(DummyFetcher):
    """A fetcher that always raises an exception."""

    def fetch(self, manufacturer_input, mpn, description):
        raise ConnectionError("Network failure")


class TestWebEvidenceProvider(unittest.TestCase):
    def test_empty_provider_not_enabled(self):
        provider = WebEvidenceProvider()
        self.assertFalse(provider.enabled)

    def test_provider_with_fetcher_is_enabled(self):
        provider = WebEvidenceProvider()
        provider.register(DummyFetcher())
        self.assertTrue(provider.enabled)

    def test_gather_returns_results(self):
        mock = MockFetcher(results=[
            WebEvidenceResult(manufacturer="Moen", brand="Moen", source_url="https://example.com", confidence=0.8, signal="Found on website"),
        ])
        provider = WebEvidenceProvider()
        provider.register(mock)
        results = provider.gather("Moen", "MN-7000", "Kitchen faucet")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].manufacturer, "Moen")
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.last_args, ("Moen", "MN-7000", "Kitchen faucet"))

    def test_gather_returns_empty_for_dummy(self):
        provider = WebEvidenceProvider()
        provider.register(DummyFetcher())
        results = provider.gather("Moen", None, None)
        self.assertEqual(len(results), 0)

    def test_gather_skips_failing_fetcher(self):
        provider = WebEvidenceProvider(delay=0)
        provider.register(FailingFetcher())
        provider.register(MockFetcher(results=[
            WebEvidenceResult(manufacturer="Delta", brand=None, source_url="https://example2.com", confidence=0.7, signal="Found"),
        ]))
        results = provider.gather("Delta", None, None)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].manufacturer, "Delta")

    def test_to_evidence_converts_correctly(self):
        provider = WebEvidenceProvider()
        results = [
            WebEvidenceResult(manufacturer="Moen", brand="Moen", source_url="https://example.com", confidence=0.8, signal="Found"),
        ]
        evidence = provider.to_evidence(results)
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].type, EvidenceType.WEB_SOURCED)
        self.assertEqual(evidence[0].value, "Moen")
        self.assertAlmostEqual(evidence[0].strength, 0.8)


class TestWebEvidenceIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = load_reference_data()

    def test_web_evidence_appears_in_field_result(self):
        mock = MockFetcher(results=[
            WebEvidenceResult(manufacturer="Moen", brand="Moen", source_url="https://moen.com", confidence=0.85, signal="Found on Moen website"),
        ])
        provider = WebEvidenceProvider(delay=0)
        provider.register(mock)

        row = {"product_id": "P001", "manufacturer": "Moen", "mpn": "MN-7000", "description": "Kitchen faucet"}
        fr = enrich_manufacturer_field(row, self.ref, web_provider=provider)

        web_evidence = [e for e in fr.evidence if e.type == EvidenceType.WEB_SOURCED]
        self.assertEqual(len(web_evidence), 1)
        self.assertEqual(web_evidence[0].value, "Moen")

    def test_no_web_evidence_when_disabled(self):
        row = {"product_id": "P002", "manufacturer": "Moen", "mpn": "MN-7000", "description": "Kitchen faucet"}
        fr = enrich_manufacturer_field(row, self.ref, web_provider=None)

        web_evidence = [e for e in fr.evidence if e.type == EvidenceType.WEB_SOURCED]
        self.assertEqual(len(web_evidence), 0)

    def test_web_evidence_failure_does_not_break_pipeline(self):
        provider = WebEvidenceProvider(delay=0)
        provider.register(FailingFetcher())

        row = {"product_id": "P003", "manufacturer": "Moen", "mpn": "MN-7000", "description": "Kitchen faucet"}
        fr = enrich_manufacturer_field(row, self.ref, web_provider=provider)
        self.assertIsNotNone(fr.value)

    def test_enrich_catalog_passes_provider(self):
        mock = MockFetcher(results=[
            WebEvidenceResult(manufacturer="Moen", brand="Moen", source_url="https://moen.com", confidence=0.8, signal="Found"),
        ])
        provider = WebEvidenceProvider(delay=0)
        provider.register(mock)

        rows = [{"product_id": "P001", "manufacturer": "Moen", "mpn": "MN-7000", "description": "Faucet"}]
        results = enrich_catalog(rows, self.ref, web_provider=provider)
        self.assertEqual(len(results), 1)
        self.assertEqual(mock.call_count, 1)

    def test_validation_source_set_when_web_evidence_present(self):
        mock = MockFetcher(results=[
            WebEvidenceResult(manufacturer="Moen", brand="Moen", source_url="https://moen.com", confidence=0.8, signal="Found"),
        ])
        provider = WebEvidenceProvider(delay=0)
        provider.register(mock)

        row = {"product_id": "P001", "manufacturer": "Moen", "mpn": "MN-7000", "description": "Faucet"}
        fr = enrich_manufacturer_field(row, self.ref, web_provider=provider)
        self.assertEqual(fr.validation.source, ValidationState.PASSED)


if __name__ == "__main__":
    unittest.main()
