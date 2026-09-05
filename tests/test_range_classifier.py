import unittest
from backend.services.range_classifier import classify_lab_result

class TestRangeClassifier(unittest.TestCase):

    def test_missing_reference_range(self):
        # Rule: If source report does not provide a range, mark UNKNOWN. Never invent!
        status, num = classify_lab_result("14.2 g/dL", None)
        self.assertEqual(status, "UNKNOWN")
        self.assertEqual(num, 14.2)

        status, num = classify_lab_result("14.2 g/dL", "Not provided")
        self.assertEqual(status, "UNKNOWN")

        status, num = classify_lab_result("14.2 g/dL", "")
        self.assertEqual(status, "UNKNOWN")

    def test_numeric_ranges(self):
        # Hemoglobin 11.2 g/dL in range 12.0 - 15.5 -> LOW
        status, num = classify_lab_result("11.2", "12.0 - 15.5")
        self.assertEqual(status, "LOW")

        # Hemoglobin 13.5 g/dL in range 12.0 - 15.5 -> NORMAL
        status, num = classify_lab_result("13.5 g/dL", "12.0 - 15.5")
        self.assertEqual(status, "NORMAL")

        # Hemoglobin 16.8 g/dL in range 12.0 - 15.5 -> HIGH
        status, num = classify_lab_result("16.8", "12.0 - 15.5")
        self.assertEqual(status, "HIGH")

    def test_inequalities(self):
        # HbA1c < 5.7 -> NORMAL for 5.4, HIGH for 6.5
        status, num = classify_lab_result("5.4 %", "< 5.7")
        self.assertEqual(status, "NORMAL")

        status, num = classify_lab_result("6.5 %", "< 5.7")
        self.assertEqual(status, "HIGH")

    def test_qualitative(self):
        status, num = classify_lab_result("Negative", "Negative")
        self.assertEqual(status, "NORMAL")

        status, num = classify_lab_result("Positive", "Negative")
        self.assertEqual(status, "HIGH")

if __name__ == "__main__":
    unittest.main()
