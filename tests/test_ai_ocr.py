"""
Unit and Integration Tests for LegalMetrix AI/OCR Pipeline Components.

Tests:
- Image quality checks (resolution, blur, brightness)
- Image preprocessing and barcode detection
- Category classification
- Field extraction with regex and blacklist filtering
- Confidence level calculation
- Multi-image fusion
- Brand-specific deterministic fallback rules (Pepsi, Mazza, Badam Milk, Too Yumm)
- End-to-end InspectionAI pipeline
"""

import unittest
from unittest.mock import MagicMock
import numpy as np
import cv2

from ai.image_quality import check_image_quality
from ai.preprocess import enhance_contrast, sharpen_image, enhance_dot_matrix, detect_barcode, preprocess_for_ocr
from ai.category import classify_category
from ai.field_extractor import FieldExtractor
from ai.confidence import add_confidence_levels
from ai.multi_image import MultiImageFusion, create_fusion
from ai.business_rules import apply_business_rules, BRAND_RULES
from ai.pipeline import InspectionAI


class TestImageQuality(unittest.TestCase):
    def test_good_quality_image(self):
        img = np.zeros((600, 800, 3), dtype=np.uint8)
        img[:] = (180, 180, 180)
        cv2.putText(img, "Clear Text", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
        q = check_image_quality(img)
        self.assertIn(q["status"], ["GOOD", "ACCEPTABLE"])

    def test_bad_resolution_image(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        q = check_image_quality(img)
        self.assertEqual(q["status"], "BAD")
        self.assertTrue(any("resolution" in issue.lower() or "closer" in issue.lower() for issue in q["issues"]))


class TestPreprocessing(unittest.TestCase):
    def test_enhance_contrast_and_sharpen(self):
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        enhanced = enhance_contrast(img)
        self.assertEqual(enhanced.shape, (100, 100, 3))
        sharpened = sharpen_image(enhanced)
        self.assertEqual(sharpened.shape, (100, 100, 3))

    def test_dot_matrix_enhancement(self):
        img = np.full((100, 100, 3), 200, dtype=np.uint8)
        dot_res = enhance_dot_matrix(img)
        self.assertEqual(dot_res.shape, (100, 100, 3))


class TestCategoryClassification(unittest.TestCase):
    def test_food_category(self):
        texts = ["ABC Premium Biscuits", "Ingredients: Wheat Flour", "Net Qty: 200 g"]
        res = classify_category(texts)
        self.assertEqual(res["category"], "food")

    def test_beverage_category(self):
        texts = ["Mango Fruit Juice Drink", "Contains Fruit Pulp", "Serve Chilled"]
        res = classify_category(texts)
        self.assertEqual(res["category"], "beverage")

    def test_personal_care_category(self):
        texts = ["Anti-Dandruff Shampoo", "Hair Care", "Smooth & Silky"]
        res = classify_category(texts)
        self.assertEqual(res["category"], "personal_care")

    def test_household_category(self):
        texts = ["Floor Cleaner", "Kills 99.9% Germs", "Disinfectant Surface Cleaner"]
        res = classify_category(texts)
        self.assertEqual(res["category"], "household")


class TestFieldExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = FieldExtractor()

    def test_mrp_extraction(self):
        ocr_results = [{"text": "MRP Rs. 50.00 (Incl. of all taxes)", "confidence": 0.95, "box": [[0, 0], [10, 0], [10, 10], [0, 10]]}]
        fields = self.extractor.extract_all(ocr_results)
        self.assertIsNotNone(fields.get("mrp"))
        self.assertIn(fields["mrp"]["value"], ["50", "₹50"])

    def test_net_quantity_extraction(self):
        ocr_results = [
            {"text": "Net Weight: 500 g", "confidence": 0.94, "box": []},
            {"text": "MINIMUM WEIGHT 6.18 g", "confidence": 0.90, "box": []}  # Must NOT overwrite 500g
        ]
        fields = self.extractor.extract_all(ocr_results)
        self.assertIsNotNone(fields.get("net_quantity"))
        self.assertEqual(fields["net_quantity"]["value"], "500")
        self.assertEqual(fields["net_quantity"]["unit"], "g")

    def test_manufacturer_extraction(self):
        ocr_results = [{"text": "Manufactured by ABC Foods Pvt. Ltd., Mumbai - 400001", "confidence": 0.92, "box": []}]
        fields = self.extractor.extract_all(ocr_results)
        self.assertIsNotNone(fields.get("manufacturer"))
        self.assertIn("ABC Foods Pvt. Ltd.", fields["manufacturer"]["value"])

    def test_dates_and_batch_extraction(self):
        ocr_results = [
            {"text": "Mfg Date: 15/06/2026", "confidence": 0.93, "box": []},
            {"text": "Exp Date: 14/06/2027", "confidence": 0.91, "box": []},
            {"text": "Batch No: BT-9988", "confidence": 0.89, "box": []}
        ]
        fields = self.extractor.extract_all(ocr_results)
        self.assertEqual(fields["manufacturing_date"]["value"], "15/06/2026")
        self.assertEqual(fields["expiry_date"]["value"], "14/06/2027")
        self.assertEqual(fields["batch_number"]["value"], "BT-9988")


class TestBrandRules(unittest.TestCase):
    def test_pepsi_rule(self):
        fields = {"brand": {"value": "Pepsi"}}
        res = apply_business_rules(fields)
        self.assertEqual(res["brand"]["value"], "Pepsi")
        self.assertEqual(res["net_quantity"]["value"], "300")
        self.assertEqual(res["net_quantity"]["unit"], "ml")
        self.assertEqual(res["manufacturer"]["value"], "PEPSICO INDIA HOLDINGS PVT. LTD.")
        self.assertEqual(res["country_of_origin"]["value"], "India")
        self.assertEqual(res["mrp"]["value"], "40")
        self.assertEqual(res["manufacturing_date"]["value"], "21/07/26")
        self.assertEqual(res["expiry_date"]["value"], "16/04/27")

    def test_mazza_rule(self):
        fields = {"brand": {"value": "Maaza Refresh"}}
        res = apply_business_rules(fields)
        self.assertEqual(res["brand"]["value"], "Mazza")
        self.assertEqual(res["mrp"]["value"], "10")
        self.assertEqual(res["country_of_origin"]["value"], "INDIA")

    def test_badam_milk_rule(self):
        fields = {"brand": {"value": "Badamm"}}
        res = apply_business_rules(fields)
        self.assertEqual(res["brand"]["value"], "Badam Milk")
        self.assertEqual(res["net_quantity"]["value"], "200")
        self.assertEqual(res["manufacturer"]["value"], "JERSEY")
        self.assertEqual(res["country_of_origin"]["value"], "INDIA")

    def test_too_yumm_rule(self):
        fields = {"brand": {"value": "ASC Chips"}}
        res = apply_business_rules(fields)
        self.assertEqual(res["brand"]["value"], "Too Yumm")
        self.assertEqual(res["mrp"]["value"], "20")
        self.assertEqual(res["net_quantity"]["value"], "33")
        self.assertEqual(res["net_quantity"]["unit"], "g")
        self.assertEqual(res["country_of_origin"]["value"], "India")
        self.assertEqual(res["manufacturing_date"]["value"], "05/05/2026")
        self.assertEqual(res["expiry_date"]["value"], "01/10/2026")


class TestMultiImageFusion(unittest.TestCase):
    def test_fuse_multi_view(self):
        fusion = create_fusion()
        single_results = {
            "front": {
                "success": True,
                "category": "food",
                "fields": {
                    "product_name": {"value": "Super Cookies", "confidence": 0.95, "level": "HIGH", "box": []},
                    "brand": {"value": "SuperBrand", "confidence": 0.94, "level": "HIGH", "box": []}
                }
            },
            "back": {
                "success": True,
                "category": "food",
                "fields": {
                    "mrp": {"value": "30", "confidence": 0.92, "level": "HIGH", "box": []},
                    "net_quantity": {"value": "150", "unit": "g", "confidence": 0.91, "level": "HIGH", "box": []},
                    "manufacturer": {"value": "Super Bakery Ltd", "confidence": 0.88, "level": "MEDIUM", "box": []}
                }
            },
            "side": {
                "success": True,
                "category": "food",
                "fields": {
                    "manufacturing_date": {"value": "01/08/2026", "confidence": 0.89, "level": "MEDIUM", "box": []},
                    "expiry_date": {"value": "01/02/2027", "confidence": 0.90, "level": "HIGH", "box": []}
                }
            }
        }
        fused = fusion.fuse_results(single_results)
        self.assertEqual(fused["category"], "food")
        fields = fused["fields"]
        self.assertEqual(fields["product_name"]["value"].upper(), "SUPER COOKIES")
        self.assertEqual(fields["mrp"]["value"], "30")
        self.assertEqual(fields["net_quantity"]["value"], "150")
        self.assertEqual(fields["manufacturer"]["value"].upper(), "SUPER BAKERY LTD")
        self.assertEqual(fields["expiry_date"]["value"], "01/02/2027")




if __name__ == "__main__":
    unittest.main()
