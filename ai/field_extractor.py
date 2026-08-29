"""
Field Extraction module.

Converts raw OCR lines into structured package declaration fields
using regex and keyword-based extraction.
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class ExtractedField:
    """Represents an extracted field with metadata."""
    value: Any = None
    confidence: float = 0.0
    box: List[List[int]] = field(default_factory=list)
    unit: Optional[str] = None
    source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "value": self.value,
            "confidence": self.confidence,
            "box": self.box
        }
        if self.unit:
            result["unit"] = self.unit
        if self.source:
            result["source"] = self.source
        return result


class FieldExtractor:
    """Extracts package declaration fields from OCR results."""
    
    # Declaration keywords - lines containing these are not product names
    DECLARATION_KEYWORDS = [
        'MRP', 'M.R.P.', 'MAXIMUM RETAIL PRICE',
        'NET', 'QUANTITY', 'QTY', 'WEIGHT', 'WT', 'VOLUME',
        'MANUFACTURED', 'MANUFACTURER',
        'PACKED', 'PACKER',
        'IMPORTED', 'IMPORTER',
        'COUNTRY', 'ORIGIN', 'MADE IN',
        'MFD', 'MFG', 'DATE', 'PACKED ON',
        'BATCH', 'LOT', 'EXP', 'EXPIRY',
        'FSSAI', 'LICENSE', 'LIC',
        'CUSTOMER CARE', 'CONSUMER CARE',
        'INGREDIENTS', 'NUTRITION',
        'BEST BEFORE', 'USE BY'
    ]
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for field extraction."""
        
        # MRP patterns - handle various formats
        # MRP Rs. 10, MRP RS 10, MRP ₹10, MRP 10/-, MRP RS. 10/-, MRP INCL. OF ALL TAXES, MRP:, ₹10, MRP RS
        self.mrp_patterns = [
            # Explicit MRP labels with currency
            re.compile(r'(?:MRP|M\.R\.P\.|MAXIMUM\s+RETAIL\s+PRICE)\s*(?:Rs\.?|INR|₹)?\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
            # MRP with /- suffix
            re.compile(r'(?:MRP|M\.R\.P\.|MAXIMUM\s+RETAIL\s+PRICE)\s*(?:Rs\.?|INR|₹)?\s*(\d+(?:\.\d+)?)\s*/\s*-', re.IGNORECASE),
            # MRP INCL. OF ALL TAXES followed by amount
            re.compile(r'(?:MRP|M\.R\.P\.)\s*INCL\.?\s*OF\s*ALL\s*TAXES\s*(?:Rs\.?|INR|₹)?\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
            # MRP: format
            re.compile(r'(?:MRP|M\.R\.P\.)\s*[:]\s*(?:Rs\.?|INR|₹)?\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
            # Just ₹ symbol with amount near MRP context
            re.compile(r'₹\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
            # MRP RS (just the label, amount on next line or nearby)
            re.compile(r'(?:MRP|M\.R\.P\.)\s*(?:RS|RS\.)?\s*$', re.IGNORECASE),
        ]
        
        # Net Quantity patterns
        self.net_qty_patterns = [
            re.compile(r'(?:NET\s+(?:QTY|QUANTITY|WT|WEIGHT|VOLUME))\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(mg|g|kg|ml|l|litre|liter)', re.IGNORECASE),
            re.compile(r'(?:NET\s+(?:QTY|QUANTITY|WT|WEIGHT|VOLUME))\s*(\d+(?:\.\d+)?)\s*(mg|g|kg|ml|l|litre|liter)', re.IGNORECASE),
            # Handle "Net Wt. 200g" format
            re.compile(r'(?:NET\s+WT\.?)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(mg|g|kg)', re.IGNORECASE),
            # Handle "Net Vol. 500ml" format
            re.compile(r'(?:NET\s+VOL\.?)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(ml|l|litre|liter)', re.IGNORECASE),
        ]
        
        # Manufacturer patterns - expanded
        self.manufacturer_patterns = [
            re.compile(r'(?:MANUFACTURED\s+BY|MANUFACTURER)\s*[:\-]?\s*(.+)', re.IGNORECASE),
            re.compile(r'(?:MANUFACTURED\s*&\s*MARKETED\s+BY)\s*[:\-]?\s*(.+)', re.IGNORECASE),
            re.compile(r'(?:MANUFACTURED\s+FOR)\s*[:\-]?\s*(.+)', re.IGNORECASE),
            re.compile(r'(?:MFG\.?\s+BY|MFD\.?\s+BY)\s*[:\-]?\s*(.+)', re.IGNORECASE),
            re.compile(r'(?:MANUF\.\s+BY)\s*[:\-]?\s*(.+)', re.IGNORECASE),
        ]
        
        # Packer patterns
        self.packer_patterns = [
            re.compile(r'(?:PACKED\s+BY|PACKER)\s*[:\-]?\s*(.+)', re.IGNORECASE),
            re.compile(r'(?:PACKAGED\s+BY)\s*[:\-]?\s*(.+)', re.IGNORECASE),
            re.compile(r'(?:PACKED\s+AT)\s*[:\-]?\s*(.+)', re.IGNORECASE),
        ]
        
        # Importer patterns
        self.importer_patterns = [
            re.compile(r'(?:IMPORTED\s+BY|IMPORTER)\s*[:\-]?\s*(.+)', re.IGNORECASE),
            re.compile(r'(?:IMPORTED\s+AND\s+MARKETED\s+BY)\s*[:\-]?\s*(.+)', re.IGNORECASE),
        ]
        
        # Country of Origin patterns
        self.country_patterns = [
            re.compile(r'(?:COUNTRY\s+OF\s+ORIGIN)\s*[:\-]?\s*(.+)', re.IGNORECASE),
            re.compile(r'(?:MADE\s+IN)\s*[:\-]?\s*(.+)', re.IGNORECASE),
            re.compile(r'(?:PRODUCT\s+OF)\s*[:\-]?\s*(.+)', re.IGNORECASE),
            re.compile(r'(?:ORIGIN)\s*[:\-]?\s*(.+)', re.IGNORECASE),
        ]
        
        # Manufacturing Date patterns
        self.mfg_date_patterns = [
            re.compile(r'(?:MFD|MFG|PACKED\s+ON|DATE\s+OF\s+MANUFACTURE|MANUFACTURED\s+ON)\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', re.IGNORECASE),
            re.compile(r'(?:MFD|MFG|PACKED\s+ON|DATE\s+OF\s+MANUFACTURE|MANUFACTURED\s+ON)\s*[:\-]?\s*(\d{1,2}[/\-]\d{4})', re.IGNORECASE),
            re.compile(r'(?:MFD|MFG|PACKED\s+ON|DATE\s+OF\s+MANUFACTURE|MANUFACTURED\s+ON)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})', re.IGNORECASE),
        ]
        
        # Expiry Date patterns
        self.exp_date_patterns = [
            re.compile(r'(?:EXP|EXPIRY|BEST\s+BEFORE|USE\s+BY|EXPIRES\s+ON)\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', re.IGNORECASE),
            re.compile(r'(?:EXP|EXPIRY|BEST\s+BEFORE|USE\s+BY|EXPIRES\s+ON)\s*[:\-]?\s*(\d{1,2}[/\-]\d{4})', re.IGNORECASE),
            re.compile(r'(?:EXP|EXPIRY|BEST\s+BEFORE|USE\s+BY|EXPIRES\s+ON)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})', re.IGNORECASE),
        ]
        
        # Batch Number patterns
        self.batch_patterns = [
            re.compile(r'(?:BATCH\s+(?:NO|NUMBER)|LOT\s+(?:NO|NUMBER)|BATCH|LOT)\s*[:\-]?\s*([A-Z0-9\-\/]+)', re.IGNORECASE),
            re.compile(r'(?:BATCH|LOT)\s*[:\-]?\s*([A-Z0-9\-\/]{3,})', re.IGNORECASE),
        ]
        
        # Brand patterns - often appears near product name or at top
        self.brand_patterns = [
            re.compile(r'(?:BRAND|TRADE\s+MARK|TM)\s*[:\-]?\s*(.+)', re.IGNORECASE),
        ]
        
        # Product name - heuristic: first non-declaration line with reasonable length
        self.declaration_regex = re.compile(
            '|'.join(re.escape(kw) for kw in self.DECLARATION_KEYWORDS),
            re.IGNORECASE
        )
    
    def is_declaration_line(self, text: str) -> bool:
        """Check if a line is a declaration (not product name)."""
        return bool(self.declaration_regex.search(text))
    
    def _normalize_mrp(self, value: str) -> str:
        """Normalize MRP value to standard format."""
        # Remove any non-digit, non-dot characters
        cleaned = re.sub(r'[^\d\.]', '', value)
        try:
            num = float(cleaned)
            # Format as ₹X or ₹X.XX
            if num == int(num):
                return f"₹{int(num)}"
            else:
                return f"₹{num:.2f}"
        except ValueError:
            return value
    
    def _is_valid_mrp_context(self, text: str, ocr_results: List[Dict[str, Any]], idx: int) -> bool:
        """Check if a number in context looks like MRP (not batch, date, barcode, etc.)."""
        text_upper = text.upper()
        # Must have MRP keyword nearby
        if any(kw in text_upper for kw in ['MRP', 'M.R.P.', 'MAXIMUM RETAIL', '₹']):
            return True
        # Check neighboring OCR items for MRP keyword
        for offset in [-2, -1, 1, 2]:
            ni = idx + offset
            if 0 <= ni < len(ocr_results):
                neighbor_text = ocr_results[ni]['text'].upper()
                if any(kw in neighbor_text for kw in ['MRP', 'M.R.P.', 'MAXIMUM RETAIL', 'INCL. OF ALL TAXES']):
                    return True
        return False
    
    def extract_mrp(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract MRP from OCR results with improved pattern matching."""
        best_match = None
        best_confidence = 0.0
        
        for i, item in enumerate(ocr_results):
            text = item['text']
            confidence = item['confidence']
            
            for pattern in self.mrp_patterns:
                matches = list(pattern.finditer(text))
                for match in matches:
                    if match.lastindex and match.lastindex >= 1:
                        value = match.group(1)
                        # Validate this looks like MRP context
                        if self._is_valid_mrp_context(text, ocr_results, i):
                            normalized = self._normalize_mrp(value)
                            if confidence > best_confidence:
                                best_confidence = confidence
                                best_match = ExtractedField(
                                    value=normalized,
                                    confidence=confidence,
                                    box=item['box']
                                )
                    # Handle patterns that match the whole label (like "MRP RS")
                    elif 'MRP' in text.upper() and ('RS' in text.upper() or '₹' in text):
                        # Look for amount in nearby items
                        for offset in [-1, 1, 2]:
                            ni = i + offset
                            if 0 <= ni < len(ocr_results):
                                neighbor_text = ocr_results[ni]['text']
                                num_match = re.search(r'(?:₹|Rs\.?|INR)?\s*(\d+(?:\.\d+)?)\s*/?\s*-?', neighbor_text)
                                if num_match:
                                    normalized = self._normalize_mrp(num_match.group(1))
                                    if ocr_results[ni]['confidence'] > best_confidence:
                                        best_confidence = ocr_results[ni]['confidence']
                                        best_match = ExtractedField(
                                            value=normalized,
                                            confidence=ocr_results[ni]['confidence'],
                                            box=ocr_results[ni]['box']
                                        )
        
        return best_match
    
    def extract_net_quantity(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract net quantity from OCR results."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item['text']
            confidence = item['confidence']
            
            for pattern in self.net_qty_patterns:
                match = pattern.search(text)
                if match and match.lastindex >= 2:
                    value = match.group(1)
                    unit = match.group(2).lower()
                    # Normalize unit
                    if unit in ['litre', 'liter']:
                        unit = 'l'
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = ExtractedField(
                            value=value,
                            confidence=confidence,
                            box=item['box'],
                            unit=unit
                        )
        
        return best_match
    
    def extract_manufacturer(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract manufacturer from OCR results."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item['text']
            confidence = item['confidence']
            
            for pattern in self.manufacturer_patterns:
                match = pattern.search(text)
                if match and match.lastindex >= 1:
                    value = match.group(1).strip()
                    # Clean up trailing punctuation
                    value = re.sub(r'[,\.]+$', '', value).strip()
                    if confidence > best_confidence and len(value) > 2:
                        best_confidence = confidence
                        best_match = ExtractedField(
                            value=value,
                            confidence=confidence,
                            box=item['box']
                        )
        
        return best_match
    
    def extract_packer(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract packer from OCR results."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item['text']
            confidence = item['confidence']
            
            for pattern in self.packer_patterns:
                match = pattern.search(text)
                if match and match.lastindex >= 1:
                    value = match.group(1).strip()
                    value = re.sub(r'[,\.]+$', '', value).strip()
                    if confidence > best_confidence and len(value) > 2:
                        best_confidence = confidence
                        best_match = ExtractedField(
                            value=value,
                            confidence=confidence,
                            box=item['box']
                        )
        
        return best_match
    
    def extract_importer(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract importer from OCR results."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item['text']
            confidence = item['confidence']
            
            for pattern in self.importer_patterns:
                match = pattern.search(text)
                if match and match.lastindex >= 1:
                    value = match.group(1).strip()
                    value = re.sub(r'[,\.]+$', '', value).strip()
                    if confidence > best_confidence and len(value) > 2:
                        best_confidence = confidence
                        best_match = ExtractedField(
                            value=value,
                            confidence=confidence,
                            box=item['box']
                        )
        
        return best_match
    
    def extract_country_of_origin(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract country of origin from OCR results."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item['text']
            confidence = item['confidence']
            
            for pattern in self.country_patterns:
                match = pattern.search(text)
                if match and match.lastindex >= 1:
                    value = match.group(1).strip()
                    value = re.sub(r'[,\.]+$', '', value).strip()
                    if confidence > best_confidence and len(value) > 1:
                        best_confidence = confidence
                        best_match = ExtractedField(
                            value=value,
                            confidence=confidence,
                            box=item['box']
                        )
        
        return best_match
    
    def extract_manufacturing_date(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract manufacturing date from OCR results."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item['text']
            confidence = item['confidence']
            
            for pattern in self.mfg_date_patterns:
                match = pattern.search(text)
                if match and match.lastindex >= 1:
                    value = match.group(1).strip()
                    # Normalize date format to DD/MM/YY or DD/MM/YYYY
                    value = self._normalize_date(value)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = ExtractedField(
                            value=value,
                            confidence=confidence,
                            box=item['box']
                        )
        
        return best_match
    
    def extract_expiry_date(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract expiry date from OCR results."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item['text']
            confidence = item['confidence']
            
            for pattern in self.exp_date_patterns:
                match = pattern.search(text)
                if match and match.lastindex >= 1:
                    value = match.group(1).strip()
                    value = self._normalize_date(value)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = ExtractedField(
                            value=value,
                            confidence=confidence,
                            box=item['box']
                        )
        
        return best_match
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date to DD/MM/YY or DD/MM/YYYY format."""
        # Replace hyphens with slashes
        date_str = date_str.replace('-', '/')
        parts = date_str.split('/')
        if len(parts) == 3:
            # Ensure day/month are 2 digits
            day = parts[0].zfill(2)
            month = parts[1].zfill(2)
            year = parts[2]
            # If year is 2 digits, keep as is; if 4 digits, keep as is
            return f"{day}/{month}/{year}"
        elif len(parts) == 2:
            # MM/YY or MM/YYYY format
            month = parts[0].zfill(2)
            year = parts[1]
            return f"01/{month}/{year}"  # Assume 1st of month
        return date_str
    
    def extract_batch_number(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract batch/lot number from OCR results."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item['text']
            confidence = item['confidence']
            
            for pattern in self.batch_patterns:
                match = pattern.search(text)
                if match and match.lastindex >= 1:
                    value = match.group(1).strip()
                    # Filter out obvious non-batch values (dates, pure numbers that could be MRP, etc.)
                    if self._is_valid_batch(value):
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = ExtractedField(
                                value=value,
                                confidence=confidence,
                                box=item['box']
                            )
        
        return best_match
    
    def _is_valid_batch(self, value: str) -> bool:
        """Check if extracted value looks like a batch number."""
        # Must contain at least one letter or be alphanumeric with special chars
        if re.match(r'^\d+$', value):
            # Pure numbers - could be confused with MRP/date/barcode
            # Accept if it has reasonable length for batch (typically 4-12 chars)
            if 4 <= len(value) <= 12:
                return True
            return False
        # Alphanumeric with possible separators
        if re.match(r'^[A-Z0-9\-\/]+$', value, re.IGNORECASE):
            if 3 <= len(value) <= 20:
                return True
        return False
    
    def extract_brand(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract brand from OCR results."""
        # First try explicit brand patterns
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item['text']
            confidence = item['confidence']
            
            for pattern in self.brand_patterns:
                match = pattern.search(text)
                if match and match.lastindex >= 1:
                    value = match.group(1).strip()
                    value = re.sub(r'[,\.]+$', '', value).strip()
                    if confidence > best_confidence and len(value) > 1:
                        best_confidence = confidence
                        best_match = ExtractedField(
                            value=value,
                            confidence=confidence,
                            box=item['box']
                        )
        
        if best_match:
            return best_match
        
        # Fallback: brand is often the first prominent text (top of package)
        # that is not a declaration and not the product name
        # We'll use a heuristic: look at top 3 non-declaration lines
        sorted_results = sorted(ocr_results, key=lambda x: x['box'][0][1] if x['box'] else 0)
        
        non_decl_lines = []
        for item in sorted_results:
            text = item['text'].strip()
            if not text or len(text) < 2:
                continue
            if self.is_declaration_line(text):
                continue
            if re.match(r'^[\d\s₹\.\,\-\:\/]+$', text):
                continue
            non_decl_lines.append(item)
            if len(non_decl_lines) >= 3:
                break
        
        # The first non-declaration line is often the brand or product name
        # If we have multiple, the first is typically brand, second is product name
        if len(non_decl_lines) >= 1:
            item = non_decl_lines[0]
            return ExtractedField(
                value=item['text'].strip(),
                confidence=item['confidence'],
                box=item['box']
            )
        
        return None
    
    def extract_product_name(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract product name using heuristic."""
        # Sort by Y position (top to bottom)
        sorted_results = sorted(ocr_results, key=lambda x: x['box'][0][1] if x['box'] else 0)
        
        non_decl_lines = []
        for item in sorted_results:
            text = item['text'].strip()
            if not text or len(text) < 3:
                continue
            if self.is_declaration_line(text):
                continue
            # Skip lines that are mostly numbers/symbols
            if re.match(r'^[\d\s₹\.\,\-\:\/]+$', text):
                continue
            non_decl_lines.append(item)
        
        # Product name is typically the second non-declaration line (after brand)
        # or the first if brand wasn't detected separately
        if len(non_decl_lines) >= 2:
            item = non_decl_lines[1]
            return ExtractedField(
                value=item['text'].strip(),
                confidence=item['confidence'],
                box=item['box']
            )
        elif len(non_decl_lines) >= 1:
            item = non_decl_lines[0]
            return ExtractedField(
                value=item['text'].strip(),
                confidence=item['confidence'],
                box=item['box']
            )
        return None
    
    def extract_all(self, ocr_results: List[Dict[str, Any]], source: str = None) -> Dict[str, Any]:
        """Extract all fields from OCR results."""
        fields = {}
        
        # Extract each field
        mrp = self.extract_mrp(ocr_results)
        if mrp:
            mrp.source = source
            fields['mrp'] = mrp.to_dict()
        else:
            fields['mrp'] = None
            
        net_qty = self.extract_net_quantity(ocr_results)
        if net_qty:
            net_qty.source = source
            fields['net_quantity'] = net_qty.to_dict()
        else:
            fields['net_quantity'] = None
            
        manufacturer = self.extract_manufacturer(ocr_results)
        if manufacturer:
            manufacturer.source = source
            fields['manufacturer'] = manufacturer.to_dict()
        else:
            fields['manufacturer'] = None
            
        packer = self.extract_packer(ocr_results)
        if packer:
            packer.source = source
            fields['packer'] = packer.to_dict()
        else:
            fields['packer'] = None
            
        importer = self.extract_importer(ocr_results)
        if importer:
            importer.source = source
            fields['importer'] = importer.to_dict()
        else:
            fields['importer'] = None
            
        country = self.extract_country_of_origin(ocr_results)
        if country:
            country.source = source
            fields['country_of_origin'] = country.to_dict()
        else:
            fields['country_of_origin'] = None
            
        mfg_date = self.extract_manufacturing_date(ocr_results)
        if mfg_date:
            mfg_date.source = source
            fields['manufacturing_date'] = mfg_date.to_dict()
        else:
            fields['manufacturing_date'] = None
            
        exp_date = self.extract_expiry_date(ocr_results)
        if exp_date:
            exp_date.source = source
            fields['expiry_date'] = exp_date.to_dict()
        else:
            fields['expiry_date'] = None
            
        batch = self.extract_batch_number(ocr_results)
        if batch:
            batch.source = source
            fields['batch_number'] = batch.to_dict()
        else:
            fields['batch_number'] = None
            
        product_name = self.extract_product_name(ocr_results)
        if product_name:
            product_name.source = source
            fields['product_name'] = product_name.to_dict()
        else:
            fields['product_name'] = None
            
        brand = self.extract_brand(ocr_results)
        if brand:
            brand.source = source
            fields['brand'] = brand.to_dict()
        else:
            fields['brand'] = None
        
        return fields


if __name__ == "__main__":
    # Test with sample OCR results
    test_ocr = [
        {"text": "MRP Rs. 50", "confidence": 0.97, "box": [[10,10],[100,10],[100,30],[10,30]]},
        {"text": "Net Qty: 200 g", "confidence": 0.96, "box": [[10,50],[150,50],[150,70],[10,70]]},
        {"text": "Manufactured by ABC Foods Ltd", "confidence": 0.91, "box": [[10,90],[300,90],[300,110],[10,110]]},
        {"text": "Mfd 08/2026", "confidence": 0.94, "box": [[10,130],[120,130],[120,150],[10,150]]},
        {"text": "Exp 08/2027", "confidence": 0.94, "box": [[10,170],[120,170],[120,190],[10,190]]},
        {"text": "Batch No: ABC123", "confidence": 0.92, "box": [[10,210],[150,210],[150,230],[10,230]]},
        {"text": "ABC Biscuits", "confidence": 0.94, "box": [[10,250],[200,250],[200,270],[10,270]]},
    ]
    
    extractor = FieldExtractor()
    fields = extractor.extract_all(test_ocr, source="test.jpg")
    
    import json
    print(json.dumps(fields, indent=2))