import unittest
from io import BytesIO

from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


class TestHealthEndpoint(unittest.TestCase):
    def test_health_returns_ok(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")

    def test_health_includes_reference_data(self):
        response = client.get("/health")
        data = response.json()
        self.assertIn("reference_data", data)
        self.assertIsInstance(data["reference_data"], dict)


class TestEnrichJsonEndpoint(unittest.TestCase):
    def test_enrich_empty_products(self):
        response = client.post("/enrich", json={"products": []})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["n_products"], 0)
        self.assertEqual(data["results"], [])

    def test_enrich_single_product(self):
        payload = {
            "products": [
                {
                    "product_id": "P001",
                    "manufacturer": "Moen",
                    "mpn": "MN-7000",
                    "description": "Single handle kitchen faucet, chrome finish",
                    "category": "Faucets",
                }
            ]
        }
        response = client.post("/enrich", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["n_products"], 1)
        self.assertIn("results", data)
        self.assertGreater(data["elapsed_seconds"], 0)

    def test_enrich_result_has_expected_fields(self):
        payload = {
            "products": [
                {
                    "product_id": "P001",
                    "manufacturer": "Moen",
                    "mpn": "MN-7000",
                    "description": "Kitchen faucet",
                    "category": "Faucets",
                }
            ]
        }
        response = client.post("/enrich", json=payload)
        data = response.json()
        result = data["results"][0]
        self.assertEqual(result["product_id"], "P001")
        self.assertIn("overall_trust", result)
        self.assertIn("overall_decision", result)
        self.assertIn("fields", result)
        self.assertIn("manufacturer", result["fields"])

    def test_enrich_field_result_structure(self):
        payload = {
            "products": [
                {
                    "product_id": "P001",
                    "manufacturer": "Moen",
                    "mpn": "MN-7000",
                    "description": "Kitchen faucet",
                    "category": "Faucets",
                }
            ]
        }
        response = client.post("/enrich", json=payload)
        data = response.json()
        mfg = data["results"][0]["fields"]["manufacturer"]
        self.assertIn("value", mfg)
        self.assertIn("confidence", mfg)
        self.assertIn("decision", mfg)
        self.assertIn("evidence", mfg)
        self.assertIn("validation", mfg)

    def test_enrich_multiple_products(self):
        payload = {
            "products": [
                {"product_id": "P001", "manufacturer": "Moen", "mpn": "MN-7000", "description": "Faucet"},
                {"product_id": "P002", "manufacturer": "Delta", "mpn": "DL-5000", "description": "Shower head"},
            ]
        }
        response = client.post("/enrich", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["n_products"], 2)

    def test_enrich_minimal_product(self):
        payload = {"products": [{"product_id": "P001"}]}
        response = client.post("/enrich", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["n_products"], 1)

    def test_enrich_invalid_json(self):
        response = client.post("/enrich", json={})
        self.assertEqual(response.status_code, 422)


class TestEnrichCsvEndpoint(unittest.TestCase):
    def test_enrich_csv_valid(self):
        csv_content = b"product_id,manufacturer,mpn,description,category\nP001,Moen,MN-7000,Kitchen faucet,Faucets\n"
        response = client.post(
            "/enrich/csv",
            files={"file": ("test.csv", BytesIO(csv_content), "text/csv")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["n_products"], 1)

    def test_enrich_csv_empty_file(self):
        csv_content = b"product_id,manufacturer,mpn,description,category\n"
        response = client.post(
            "/enrich/csv",
            files={"file": ("empty.csv", BytesIO(csv_content), "text/csv")},
        )
        self.assertEqual(response.status_code, 400)

    def test_enrich_csv_invalid_extension(self):
        response = client.post(
            "/enrich/csv",
            files={"file": ("test.txt", BytesIO(b"hello"), "text/plain")},
        )
        self.assertEqual(response.status_code, 400)

    def test_enrich_csv_malformed(self):
        response = client.post(
            "/enrich/csv",
            files={"file": ("bad.csv", BytesIO(b"\x00\x01\x02"), "text/csv")},
        )
        self.assertEqual(response.status_code, 400)

    def test_enrich_csv_multiple_rows(self):
        csv_content = (
            b"product_id,manufacturer,mpn,description,category\n"
            b"P001,Moen,MN-7000,Kitchen faucet,Faucets\n"
            b"P002,Delta,DL-5000,Shower head,Bathroom\n"
        )
        response = client.post(
            "/enrich/csv",
            files={"file": ("multi.csv", BytesIO(csv_content), "text/csv")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["n_products"], 2)


class TestOpenAPIDocs(unittest.TestCase):
    def test_docs_endpoint_available(self):
        response = client.get("/docs")
        self.assertEqual(response.status_code, 200)

    def test_openapi_schema_available(self):
        response = client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("paths", data)
        self.assertIn("/health", data["paths"])
        self.assertIn("/enrich", data["paths"])
        self.assertIn("/enrich/csv", data["paths"])


if __name__ == "__main__":
    unittest.main()
