import unittest
import os
import io
import fitz # PyMuPDF
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.services.pdf_parser import extract_text_from_file
from backend.services.ai_extractor import extract_structured_data
from backend.services.range_classifier import classify_lab_result

client = TestClient(app)

class TestPDFPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a test PDF file matching Rohan Mehta's laboratory report
        cls.pdf_path = "test_rohan_mehta_report.pdf"
        doc = fitz.open()
        page = doc.new_page()
        text_content = """METROPOLITAN CLINICAL LABORATORY REPORT
Patient Details:
Patient Name: Rohan Mehta
Age / Sex: 61 Y / Male
Report Date: 12-May-2025
Referred By: Dr. A. Sharma

COMPLETE BLOOD COUNT & METABOLIC PANEL
----------------------------------------------------------------------
Test Description        Result      Units       Reference Range
----------------------------------------------------------------------
Hemoglobin              12.4        g/dL        13.0 - 17.0
WBC Count               7.2         10^3/uL     4.5 - 11.0
Platelets               250         10^3/uL     150 - 450
Fasting Glucose         126         mg/dL       70 - 99
Total Cholesterol       232         mg/dL       < 200
LDL Cholesterol         145         mg/dL       < 100
HDL Cholesterol         42          mg/dL       >= 40
Triglycerides           180         mg/dL       < 150
Serum Creatinine        1.1         mg/dL       0.7 - 1.3
ALT (SGPT)              35          U/L         7 - 56
----------------------------------------------------------------------
End of Laboratory Report
"""
        page.insert_text((50, 50), text_content, fontsize=10)
        doc.save(cls.pdf_path)
        doc.close()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.pdf_path):
            os.remove(cls.pdf_path)

    def test_pdf_text_extraction(self):
        result = extract_text_from_file(self.pdf_path)
        self.assertIn("text", result)
        self.assertIn("Rohan Mehta", result["text"])
        self.assertIn("Hemoglobin", result["text"])
        self.assertGreater(len(result["text"]), 100)

    def test_structured_lab_extraction(self):
        parsed_text = extract_text_from_file(self.pdf_path)["text"]
        payload = extract_structured_data(parsed_text, "test_rohan_mehta_report.pdf")
        
        # Check header info
        header = payload.get("header_info", {})
        self.assertEqual(header.get("patient_name"), "Rohan Mehta")
        self.assertEqual(header.get("age"), 61)
        self.assertEqual(header.get("sex"), "Male")

        # Check lab results extraction (should extract all 10 tests)
        labs = payload.get("lab_results", [])
        self.assertEqual(len(labs), 10, f"Expected 10 extracted lab tests, got {len(labs)}")

        lab_dict = {l["test_name"]: l for l in labs}

        # Validate Hemoglobin: 12.4 g/dL, range 13.0 - 17.0 -> LOW
        self.assertIn("Hemoglobin", lab_dict)
        hgb = lab_dict["Hemoglobin"]
        self.assertEqual(hgb["value"], "12.4")
        self.assertEqual(hgb["status"], "LOW")

        # Validate Total Cholesterol: 232 mg/dL, range < 200 -> HIGH
        self.assertIn("Total Cholesterol", lab_dict)
        chol = lab_dict["Total Cholesterol"]
        self.assertEqual(chol["value"], "232")
        self.assertEqual(chol["status"], "HIGH")

        # Validate HDL: 42 mg/dL, range >= 40 -> NORMAL
        self.assertIn("HDL", lab_dict)
        hdl = lab_dict["HDL"]
        self.assertEqual(hdl["value"], "42")
        self.assertEqual(hdl["status"], "NORMAL")

    def test_api_document_upload_integration(self):
        import uuid
        code = f"PAT-ROHAN-{uuid.uuid4().hex[:6]}"
        # 1. Create a patient record via API
        create_res = client.post("/api/patients", json={
            "patient_id_code": code,
            "display_name": "Rohan Mehta",
            "symptoms": [],
            "conditions": [],
            "allergies": [],
            "medications": []
        })
        self.assertEqual(create_res.status_code, 200)
        patient_id = create_res.json()["id"]

        # 2. Upload the PDF file
        with open(self.pdf_path, "rb") as f:
            upload_res = client.post(
                f"/api/patients/{patient_id}/documents",
                files={"file": ("test_rohan_mehta_report.pdf", f, "application/pdf")}
            )
        self.assertEqual(upload_res.status_code, 200)
        self.assertEqual(upload_res.json()["extracted_count"], 10)

        # 3. Retrieve patient record and verify demographics auto-update and lab results
        rec_res = client.get(f"/api/patients/{patient_id}/record")
        self.assertEqual(rec_res.status_code, 200)
        rec_data = rec_res.json()

        patient_info = rec_data["patient"]
        self.assertEqual(patient_info["display_name"], "Rohan Mehta")
        self.assertEqual(patient_info["age"], 61)
        self.assertEqual(patient_info["sex"], "Male")

        labs = rec_data["lab_results"]
        self.assertEqual(len(labs), 10)

        # Check summary existence
        self.assertIsNotNone(rec_data["summary"])
        self.assertIn("Rohan Mehta", rec_data["summary"]["text_summary"])

if __name__ == "__main__":
    unittest.main()
