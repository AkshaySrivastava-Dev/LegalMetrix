# Legal Metrology Rules Provenance & Statutory Framework

## 1. Primary Statutory Authority
- **Enactment**: *The Legal Metrology Act, 2009 (No. 1 of 2010)*, Ministry of Consumer Affairs, Food and Public Distribution, Department of Consumer Affairs, Government of India.
- **Principal Rules**: *Legal Metrology (Packaged Commodities) Rules, 2011* (Notification G.S.R. 202(E) dated 7th March 2011, effective from 1st April 2011).

## 2. Key Statutory Amendments & Effective Dates
1. **Legal Metrology (Packaged Commodities) Amendment Rules, 2017**:
   - *Notification*: G.S.R. 629(E) dated 23rd June 2017 (effective from **1st January 2018**).
   - *Key Provisions*:
     - Mandatory declarations on e-commerce marketplaces (Rule 6(10)).
     - Name and country of origin on all imported packages.
     - Enhanced minimum font height provisions for net quantity and MRP declarations (Rule 9).
2. **Legal Metrology (Packaged Commodities) Amendment Rules, 2021**:
   - *Notification*: G.S.R. 779(E) dated 2nd November 2021 (effective from **1st December 2022**).
   - *Key Provisions*:
     - **Mandatory Unit Sale Price (USP)** declaration on all packaged commodities (Rule 6(1)(ea) & Rule 6(11)) in standard metric terms (per gram/kg or per ml/litre or per piece).
     - Standardized declaration of month and year of manufacture or packaging across all commodity categories.
     - Relaxation of Schedule II rigid standard pack sizes for specified commodities.
3. **Legal Metrology (Packaged Commodities) (Second Amendment) Rules, 2022 & 2023**:
   - Electronic QR Code provisions for supplementary product details on non-food/electronic goods while maintaining mandatory physical declarations on the Principal Display Panel (PDP).

## 3. Statutory Clauses Implemented in LegalMetrix Engine

| Field / Declaration | Legal Provision | Requirement Description | Engine Validator |
| :--- | :--- | :--- | :--- |
| **Product Name** | Rule 6(1)(b) | Generic or common name of the commodity on Principal Display Panel | `presence`, `pattern` |
| **Net Quantity** | Rule 6(1)(c) & Rule 11 | Net quantity in standard metric units (g, kg, ml, L, m, mm, units/pieces) | `presence`, `metric_units` |
| **Maximum Retail Price (MRP)** | Rule 6(1)(e) | Maximum Retail Price inclusive of all taxes in Indian Rupees (`₹` or `Rs.`) | `presence`, `numeric_bounds` |
| **Unit Sale Price (USP)** | Rule 6(1)(ea) & Rule 6(11) | Mandatory unit sale price calculated per standard unit (e.g. ₹/g, ₹/kg, ₹/ml, ₹/L) | `validate_unit_sale_price` |
| **Manufacturer / Packer / Importer** | Rule 6(1)(a) | Name and complete address of the manufacturer, packer, or importer | `presence` |
| **Country of Origin** | Rule 6(10) | Country of origin on all manufactured or imported commodities | `presence`, `iso_country` |
| **Date of Manufacture / Packing** | Rule 6(1)(d) | Month and year of manufacture, packing, or pre-packing | `presence`, `date_format` |
| **Consumer Care Details** | Rule 6(1)(g) | Name, address, telephone number, and email address for consumer grievances | `presence`, `contact_details` |
| **Dual Pricing Prohibition** | Section 36(1) & Rule 18(2) | Prohibition of selling or offering for sale at a price higher than the declared MRP | `reconciliation_comparator` |

## 4. Statutory Food Safety & Labelling Reference
- **Regulations**: *Food Safety and Standards (Labelling and Display) Regulations, 2020* (F. No. 1-94/FSSAI/SP(L&C)/2017).
- **Mandatory Ingredient Labelling**: Rule 5(2) - Ingredients must be listed in descending order of weight or volume at the time of manufacture.
- **Mandatory Statutory Declarations**:
  - Artificial Sweeteners: Rule 6(1) (Advisory declaration regarding children & phenylketonurics).
  - Monosodium Glutamate: FSSR Rule 2.2.1 (Advisory declaration: Not recommended for infants below 12 months).
  - Synthetic Colours: Mandatory statement `CONTAINS PERMITTED SYNTHETIC FOOD COLOUR(S)`.
  - Major Allergens: FSSR Allergen Labelling (Gluten, Nuts, Soy, Milk, Fish, Egg).
