import unittest
from backend.models import Patient, Document, LabResult
from backend.services.conflict_detector import detect_patient_conflicts

class TestConflictDetector(unittest.TestCase):

    def test_age_conflict_detection(self):
        patient = Patient(
            id=1,
            patient_id_code="P-101",
            display_name="John Doe",
            age=45,
            medications=[
                {"name": "Metformin", "dose": "500mg", "source": "User Provided"},
                {"name": "Metformin", "dose": "1000mg", "source": "Prescription PDF"}
            ]
        )
        doc = Document(filename="Report.pdf", raw_text="Patient Name: John Doe\nAge: 48\nSex: Male")
        patient.documents = [doc]
        patient.lab_results = []

        conflicts = detect_patient_conflicts(patient, None)
        self.assertGreaterEqual(len(conflicts), 2)
        
        # Check age conflict
        age_conflict = next(c for c in conflicts if c["conflict_type"] == "Demographic")
        self.assertEqual(age_conflict["source_a_value"], "45 years")
        self.assertEqual(age_conflict["source_b_value"], "48 years")

        # Check medication conflict
        med_conflict = next(c for c in conflicts if c["conflict_type"] == "Medication Dosage Mismatch")
        self.assertEqual(med_conflict["field_name"], "Medication: Metformin")

if __name__ == "__main__":
    unittest.main()
