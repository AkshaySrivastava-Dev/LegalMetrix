/**
 * Client-Side Statutory Safety Watchlist & Allergen Analyzer for LegalMetrix.
 * Provides offline-first safety verification and statutory advisory analysis.
 *
 * CRITICAL POLICY:
 * - Never claims a component is inherently harmful or unsafe.
 * - Categorizes items objectively as "Safety Review Required" with clear statutory references.
 */

export const DEFAULT_SAFETY_WATCHLIST = [
  {
    id: "WL-FLV-001",
    name: "Monosodium Glutamate (MSG)",
    code: "INS 621 / E621",
    category: "Flavor Enhancer",
    patterns: [/\b(monosodium\s+glutamate|msg|ins\s*621|e\s*621|glutamate|ajinomoto)\b/i],
    reason: "Statutory advisory disclosure required under FSSR (Packaging & Labelling). Mandatory notice: Not recommended for infants below 12 months.",
    statutoryRef: "FSSAI Reg. 2.2.1 / Legal Metrology Schedule"
  },
  {
    id: "WL-SWT-001",
    name: "Aspartame (Artificial Sweetener)",
    code: "INS 951 / E951",
    category: "Artificial Sweetener",
    patterns: [/\b(aspartame|ins\s*951|e\s*951)\b/i],
    reason: "Statutory warning mandatory on principal display panel: 'Contains Artificial Sweetener & Phenylalanine. Not recommended for children or phenylketonurics.'",
    statutoryRef: "FSSAI (Food Product Standards & Food Additives) Reg. 3.1.3"
  },
  {
    id: "WL-SWT-002",
    name: "Sucralose / Non-Caloric Sweetener",
    code: "INS 955 / E955",
    category: "Artificial Sweetener",
    patterns: [/\b(sucralose|ins\s*955|e\s*955|acesulfame\s*k|ins\s*950|e\s*950|saccharin|ins\s*954)\b/i],
    reason: "Non-caloric sweetener requires statutory quantitative declaration in mg/kg and 'Not recommended for children' advisory.",
    statutoryRef: "FSSAI Labelling Reg. 2020 / Rule 6"
  },
  {
    id: "WL-PRS-001",
    name: "Sodium Benzoate / Class II Preservative",
    code: "INS 211 / E211",
    category: "Preservative",
    patterns: [/\b(sodium\s+benzoate|ins\s*211|e\s*211|class\s*ii\s*preservative|preservative\s*\(?211\)?)\b/i],
    reason: "Class II preservative subject to statutory Maximum Permissible Limits (MPL) in PPM under Food Safety Regulations.",
    statutoryRef: "FSSAI Food Additives Schedule 1"
  },
  {
    id: "WL-PRS-002",
    name: "Potassium Sorbate / Sulphites",
    code: "INS 202 / E202",
    category: "Preservative",
    patterns: [/\b(potassium\s+sorbate|ins\s*202|e\s*202|sodium\s+metabisulphite|ins\s*223|e\s*223|sulphite|sulfite)\b/i],
    reason: "Chemical preservative requiring statutory category declaration and permissible ppm threshold monitoring.",
    statutoryRef: "FSSAI Food Additives Schedule 1"
  },
  {
    id: "WL-COL-001",
    name: "Permitted Synthetic Food Colour (Tartrazine / Sunset Yellow)",
    code: "INS 102 / INS 110",
    category: "Synthetic Colour",
    patterns: [/\b(tartrazine|ins\s*102|e\s*102|sunset\s+yellow|ins\s*110|e\s*110|allura\s+red|ins\s*129|e\s*129|brilliant\s+blue|ins\s*133|synthetic\s+food\s+colou?r|synthetic\s+colou?r)\b/i],
    reason: "Mandatory statutory declaration required on display label: 'CONTAINS PERMITTED SYNTHETIC FOOD COLOUR(S)'.",
    statutoryRef: "Legal Metrology Rules 2011 & FSSAI 2.4.5"
  },
  {
    id: "WL-FAT-001",
    name: "Palm Oil / Hydrogenated Vegetable Fat",
    code: "FAT-SURV-01",
    category: "Fats & Oils",
    patterns: [/\b(palm\s+oil|palmolein|hydrogenated\s+vegetable\s+oil|vanaspati|trans\s+fat|interesterified\s+vegetable\s+fat)\b/i],
    reason: "Statutory nutritional declaration of saturated fat and trans-fat percentage per 100g/serving required under FSSAI Labelling Regulations.",
    statutoryRef: "FSSAI Mandatory Nutritional Labelling Amendment"
  },
  {
    id: "WL-ALG-001",
    name: "Major Food Allergen (Gluten / Wheat / Nuts / Soy / Milk)",
    code: "ALLERGEN-FSSAI",
    category: "Allergen Advisory",
    patterns: [/\b(gluten|wheat\s+flour|maida|peanut|groundnut|tree\s+nuts?|almonds?|cashews?|soya?|soy\s+lecithin|milk\s+solids?|lactose|casein|crustacean|fish|egg)\b/i],
    reason: "Mandatory allergen declaration required under FSSAI Labelling Regulations (in bold or separate 'Contains' statement).",
    statutoryRef: "FSSAI (Labelling and Display) Regulations 2020"
  }
];

/**
 * Analyze ingredients text or list against the statutory safety watchlist.
 * @param {string} ingredientsText 
 * @param {Array<string>} [ingredientsList] 
 * @param {Array<Object>} [customWatchlist] 
 * @returns {Object} Safety analysis result
 */
export function analyzeSafetyWatchlist(ingredientsText, ingredientsList = [], customWatchlist = null) {
  const watchlist = customWatchlist || DEFAULT_SAFETY_WATCHLIST;
  const fullText = [ingredientsText || '', ...(ingredientsList || [])].join(' ');

  const flaggedComponents = [];
  const seenIds = new Set();

  if (fullText.trim()) {
    for (const entry of watchlist) {
      if (seenIds.has(entry.id)) continue;
      for (const pattern of entry.patterns) {
        const match = fullText.match(pattern);
        if (match) {
          seenIds.add(entry.id);
          flaggedComponents.push({
            id: entry.id,
            name: entry.name,
            code: entry.code,
            category: entry.category,
            detectedToken: match[0],
            reason: entry.reason,
            statutoryReference: entry.statutoryRef || "FSSAI / Legal Metrology"
          });
          break;
        }
      }
    }
  }

  const reviewRequired = flaggedComponents.length > 0;
  return {
    status: reviewRequired ? "SAFETY_REVIEW_REQUIRED" : "COMPLIANT_DECLARATION",
    reviewRequired,
    summary: reviewRequired
      ? `Safety Review Required: ${flaggedComponents.length} statutory advisory component(s) detected.`
      : "Ingredients declaration analyzed. No statutory watchlist advisories flagged.",
    flaggedCount: flaggedComponents.length,
    flaggedComponents,
    extractedIngredients: ingredientsList || [],
    rawIngredientsText: ingredientsText || ""
  };
}
