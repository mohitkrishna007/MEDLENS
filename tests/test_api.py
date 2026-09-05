import unittest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

class TestMedLensAPI(unittest.TestCase):

    def test_health_check(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_demo_seed_workflow(self):
        # 1. Trigger demo seed
        seed_res = client.post("/api/demo/seed")
        self.assertEqual(seed_res.status_code, 200)
        patient_id = seed_res.json()["patient_id"]

        # 2. Get patient record
        rec_res = client.get(f"/api/patients/{patient_id}/record")
        self.assertEqual(rec_res.status_code, 200)
        data = rec_res.json()

        self.assertEqual(data["patient"]["patient_id_code"], "PAT-2025-089")
        self.assertGreaterEqual(len(data["documents"]), 5)
        self.assertGreaterEqual(len(data["lab_results"]), 7)
        self.assertGreaterEqual(len(data["conflicts"]), 2)

        # 3. Test reference range rule: Hs-CRP should be UNKNOWN since range was omitted
        hscrp_lab = next(l for l in data["lab_results"] if l["test_name"] == "Hs-CRP")
        self.assertEqual(hscrp_lab["status"], "UNKNOWN")
        self.assertEqual(hscrp_lab["reference_range"], "Not provided in source")

        # 4. Test PDF export endpoint
        export_res = client.get(f"/api/patients/{patient_id}/export")
        self.assertEqual(export_res.status_code, 200)
        self.assertEqual(export_res.headers["content-type"], "application/pdf")

if __name__ == "__main__":
    unittest.main()
