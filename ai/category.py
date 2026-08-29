"""
Product Category classification using keyword heuristics.

Classifies products into: food, beverage, personal_care, household, or unknown.
"""

import re
from typing import Dict, List, Tuple, Optional, Any


# Category keywords with weights
CATEGORY_KEYWORDS = {
    "food": {
        "keywords": [
            "biscuit", "biscuits", "cookie", "cookies", "cracker", "crackers", "bread", "cake", "pastry",
            "chocolate", "candy", "sweet", "confectionery", "toffee",
            "snack", "chips", "namkeen", "mixture", "bhujia",
            "noodle", "pasta", "vermicelli", "spaghetti", "macaroni",
            "rice", "flour", "atta", "maida", "suji", "besan",
            "dal", "pulse", "bean", "lentil", "chana", "rajma",
            "spice", "masala", "turmeric", "chilli", "coriander", "cumin",
            "oil", "ghee", "butter", "vanaspati", "cooking oil",
            "sauce", "ketchup", "chutney", "pickle", "achaar",
            "jam", "jelly", "marmalade", "honey", "syrup",
            "cereal", "cornflakes", "oats", "muesli", "granola",
            "milk", "curd", "yogurt", "cheese", "paneer", "dairy",
            "ice cream", "frozen", "dessert", "pudding",
            "instant", "ready to eat", "ready to cook",
            "ingredients", "nutrition", "energy", "protein", "vitamin",
            "wheat", "maize", "barley", "millet", "grain",
            "sugar", "salt", "pepper", "herb", "seasoning"
        ],
        "weight": 1.0
    },
    "beverage": {
        "keywords": [
            "juice", "juices", "nectar", "drink", "drinks", "beverage", "beverages", "squash", "cordial",
            "soft drink", "soda", "cola", "pepsi", "coke", "fanta",
            "water", "mineral water", "packaged water", "spring water",
            "tea", "coffee", "instant coffee", "green tea", "black tea",
            "milk shake", "lassi", "buttermilk", "chaas",
            "energy drink", "sports drink", "electrolyte",
            "alcohol", "beer", "wine", "whisky", "vodka", "rum",
            "fruit drink", "fruit juice", "vegetable juice",
            "concentrate", "syrup", "sherbet",
            "carbonated", "aerated", "fizzy"
        ],
        "weight": 1.0
    },
    "personal_care": {
        "keywords": [
            "shampoo", "shampoos", "conditioner", "conditioners", "hair oil", "hair gel", "hair cream",
            "soap", "soaps", "body wash", "shower gel", "bath soap", "liquid soap",
            "toothpaste", "toothbrush", "mouthwash", "dental floss", "dental",
            "cream", "creams", "lotion", "lotions", "moisturizer", "sunscreen", "sunblock",
            "deodorant", "antiperspirant", "perfume", "deo", "body spray",
            "face wash", "cleanser", "toner", "serum", "face cream",
            "lip balm", "lipstick", "kajal", "eyeliner", "mascara",
            "nail polish", "nail paint", "manicure", "pedicure",
            "razor", "blade", "shaving cream", "shaving foam", "aftershave",
            "talc", "powder", "prickly heat", "cooling",
            "sanitizer", "hand wash", "hand sanitizer", "germ protection",
            "diaper", "sanitary", "pad", "tampon", "menstrual",
            "baby oil", "baby cream", "baby powder", "baby wash",
            "skin care", "hair care", "personal care", "cosmetic",
            "dermatologist", "clinically tested", "hypoallergenic"
        ],
        "weight": 1.0
    },
    "household": {
        "keywords": [
            "detergent", "detergents", "washing powder", "laundry", "soap powder", "liquid detergent",
            "fabric softener", "conditioner", "stain remover", "bleach",
            "dish wash", "dishwash", "dish soap", "dish liquid", "bar",
            "floor cleaner", "toilet cleaner", "bathroom cleaner", "surface cleaner",
            "glass cleaner", "window cleaner", "multi surface", "all purpose",
            "disinfectant", "sanitizer", "germ kill", "antibacterial", "antiviral",
            "air freshener", "room freshener", "mosquito", "insect", "repellent",
            "coil", "liquid vaporizer", "spray", "aerosol",
            "garbage bag", "trash bag", "bin liner", "zip lock",
            "aluminum foil", "cling film", "plastic wrap", "baking paper",
            "scrubber", "sponge", "scrub pad", "steel wool", "wiper",
            "mop", "broom", "brush", "dustpan", "bucket",
            "cleaner", "cleaning", "wash", "polish", "shine",
            "phenyl", "acid", "harpic", "domex", "lizol", "colin"
        ],
        "weight": 1.0
    }
}


def classify_category(ocr_texts: List[str]) -> Dict[str, Any]:
    """
    Classify product category based on OCR text keywords.
    
    Args:
        ocr_texts: List of text strings from OCR
        
    Returns:
        Dict with category and score
    """
    # Combine all texts
    combined_text = " ".join(ocr_texts).lower()
    
    scores = {}
    
    for category, data in CATEGORY_KEYWORDS.items():
        score = 0
        matched_keywords = []
        
        for keyword in data["keywords"]:
            # Use word boundary matching for better accuracy
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            matches = len(re.findall(pattern, combined_text))
            if matches > 0:
                score += matches * data["weight"]
                matched_keywords.append(keyword)
        
        scores[category] = {
            "score": score,
            "matched_keywords": matched_keywords
        }
    
    # Find category with highest score
    best_category = "unknown"
    best_score = 0
    
    for category, data in scores.items():
        if data["score"] > best_score:
            best_score = data["score"]
            best_category = category
    
    # Require minimum score to be confident
    if best_score < 1:
        best_category = "unknown"
    
    return {
        "category": best_category,
        "score": best_score,
        "details": scores
    }


if __name__ == "__main__":
    # Test cases
    test_cases = [
        (["Biscuits Ingredients Nutrition", "Wheat Flour Sugar"], "food"),
        (["Shampoo Conditioner", "Hair Care Anti Dandruff"], "personal_care"),
        (["Juice Beverage", "Fruit Drink Orange"], "beverage"),
        (["Detergent Washing Powder", "Fabric Softener"], "household"),
        (["Random Product XYZ", "Unknown Brand"], "unknown"),
        (["Chocolate Biscuits", "Wheat Flour Sugar Cocoa"], "food"),
        (["Toothpaste Dental Cream", "Cavity Protection"], "personal_care"),
        (["Floor Cleaner Disinfectant", "Kills Germs"], "household"),
    ]
    
    for texts, expected in test_cases:
        result = classify_category(texts)
        print(f"Input: {texts}")
        print(f"Expected: {expected}, Got: {result['category']} (score: {result['score']})")
        if result['category'] != 'unknown':
            print(f"Matched: {result['details'][result['category']]['matched_keywords']}")
        else:
            print("Matched: []")
        print()