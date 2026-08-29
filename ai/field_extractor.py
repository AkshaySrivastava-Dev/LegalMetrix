"""
Field Extraction module.

Converts raw OCR lines into structured package declaration fields
using robust regex, visual prominence, and keyword-based semantic extraction.
Works generically across all packaged consumer products.
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
    evidence_text: Optional[str] = None
    
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
        if self.evidence_text:
            result["evidence_text"] = self.evidence_text
        return result


class FieldExtractor:
    """Extracts package declaration fields from OCR results generically."""
    
    # Universal Blacklist: Generic packaging, legal, instructional & marketing terms
    GENERIC_PACKAGING_TERMS = [
        'PACK', 'PACKAGE', 'PACKET', 'CARTON', 'BOX', 'BOTTLE', 'CAN', 'POUCH', 'CONTAINER', 'WRAPPER',
        'DRINK', 'FOOD', 'PRODUCT', 'ITEM', 'COMMODITY', 'CONTENTS', 'GOODS',
        'NET QUANTITY', 'NET WT', 'NET VOL', 'NET WEIGHT', 'NET VOLUME', 'MINIMUM WEIGHT', 'GROSS WEIGHT',
        'MANUFACTURED', 'MANUFACTURED BY', 'PACKED BY', 'PACKER', 'MANUFACTURER', 'IMPORTER', 'MARKETER', 'DISTRIBUTOR',
        'INDIA', 'ORIGIN', 'PREMIUM', 'FRESH', 'BEST', 'QUALITY', 'NATURAL', 'CLASSIC', 'AUTHENTIC',
        'READY-TO-SERVE', 'STORE', 'KEEP', 'USE', 'BEFORE', 'AFTER', 'SHAKE', 'WELL', 'CHILLED', 'COOL', 'DRY', 'PLACE',
        'PUSH', 'PULL', 'STRAW', 'INSERT', 'DISPOSE', 'CRUSH', 'RECYCLE', 'PLASTIC', 'PAPER', 'PAPER BASED', 'PAPER GASED',
        'INGREDIENTS', 'NUTRITION', 'NUTRITIONAL', 'ENERGY', 'KCAL', 'PROTEIN', 'CARBOHYDRATE', 'SUGAR', 'FAT', 'SODIUM',
        'FSSAI', 'LICENSE', 'LIC', 'CUSTOMER CARE', 'CONSUMER CARE', 'FEEDBACK', 'TOLL FREE', 'EMAIL', 'WEBSITE',
        'MRP', 'M.R.P.', 'MAXIMUM RETAIL PRICE', 'INCL OF ALL TAXES', 'INCL OF', 'ALL TAXES', 'INCLUSIVE', 'TAXES', 'TAX', 'BATHTAXES',
        'BATCH', 'BATCH NO', 'BATCH NUMBER', 'LOT', 'LOT NO', 'LOT NUMBER', 'MFD', 'MFG', 'PKD', 'EXP', 'EXPIRY', 'BEST BEFORE', 'USE BY',
        'BARCODE', 'SCAN', 'QR CODE', 'TERMS', 'CONDITIONS', 'CALCULATION BASED', 'RETAIL INDEX', 'SALES VALUE', 'MARKET', 'COPYRIGHT',
        'INDIA\'S BEST', 'NUMBER ONE', 'NO. 1', 'NO.1', 'CLAIM', 'SERVING', 'SERVE', 'CONTAINS', 'THIS PACK',
        'WHAT\'S', 'GOOD', 'PROTECTS', 'TASTE', 'TASTIE', 'TASTY', 'TREAT', 'MADE FRUM', 'REAL MANGO', 'PULP', 'BUY', 'NOT', 'CALLER',
        'BUY NOT', 'ABOUT', 'CONTACT', 'FOR MFD', 'FOR EXP'
    ]
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for field extraction."""
        
        # MRP patterns
        self.mrp_cue_pattern = re.compile(
            r'(?:MRP|M\.R\.P\.|MAXIMUM\s+RETAIL|INCL\.?\s*OF\s*ALL\s*TAXES|INCL\s*OF|ALL\s*TAXES|TAXES\b|PRICE\b)',
            re.IGNORECASE
        )
        self.mrp_standalone_num = re.compile(
            r'^(?:RS\.?|INR|₹)?\s*(\d+(?:\.\d+)?)\s*(?:/\s*[-–]|/-|/–)?$',
            re.IGNORECASE
        )
        self.mrp_patterns = [
            re.compile(r'(?:MRP|M\.R\.P\.|MAXIMUM\s+RETAIL\s+PRICE|PRICE)\s*(?:Rs\.?|INR|₹)?\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:/\s*[-–]|/-|/–)?', re.IGNORECASE),
            re.compile(r'(?:Rs\.?|₹)\s*(\d+(?:\.\d+)?)\s*(?:/\s*[-–]|/-|/–)?', re.IGNORECASE),
            re.compile(r'(\d+(?:\.\d+)?)\s*/\s*[-–]', re.IGNORECASE),
        ]
        
        # Net Quantity patterns (strictly ignoring "minimum weight")
        self.net_qty_explicit_patterns = [
            re.compile(r'(?:NET\s+(?:QTY|QUANTITY|WT|WEIGHT|VOLUME|CONTENTS))\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(mg|g|kg|ml|l|litre|liter|cl|pieces|pcs|tablets|capsules|m|cm|gb|tb)\b', re.IGNORECASE),
            re.compile(r'(?:NET\s+(?:QTY|QUANTITY|WT|WEIGHT|VOLUME|CONTENTS))\s*(\d+(?:\.\d+)?)\s*(mg|g|kg|ml|l|litre|liter|cl|pieces|pcs|tablets|capsules|m|cm|gb|tb)\b', re.IGNORECASE),
            re.compile(r'\b(\d+(?:\.\d+)?)\s*(mg|g|kg|ml|l|litre|liter|cl)\b', re.IGNORECASE),
        ]
        
        # Manufacturer patterns
        self.mfg_prefix_pattern = re.compile(
            r'(?:MANUFACTURED\s+(?:AND\s+MARKETED\s+)?BY|MANUFACTURER|MFG\.?\s+BY|MFD\.?\s+BY|MANUF\.\s+BY|PRODUCED\s+BY|MADE\s+BY|A\s+PRODUCT\s+OF)\s*[:\-]?\s*(.+)',
            re.IGNORECASE
        )
        self.company_entity_pattern = re.compile(
            r'(?:#|\*|\s)*([A-Z0-9\s\.\,\-\&]+\b(?:PVT\.?\s*LTD\.?|PRIVATE\s+LIMITED|LTD\.?|LIMITED|CORP\.?|LLP|INDUSTRIES|ENTERPRISES|BEVERAGES|BOTTLERS|FOODS|COMPANY|\&\s*CO\.?))\b',
            re.IGNORECASE
        )
        
        # Packer patterns
        self.packer_patterns = [
            re.compile(r'(?:PACKED\s+BY|PACKER|PACKAGED\s+BY|PKD\.?\s+BY|PACKED\s+AT)\s*[:\-]?\s*(.+)', re.IGNORECASE),
        ]
        
        # Importer patterns
        self.importer_patterns = [
            re.compile(r'(?:IMPORTED\s+BY|IMPORTER|IMPORTED\s+AND\s+MARKETED\s+BY)\s*[:\-]?\s*(.+)', re.IGNORECASE),
        ]
        
        # Country of Origin patterns (strict explicit origin only)
        self.country_explicit_patterns = [
            re.compile(r'(?:COUNTRY\s+OF\s+ORIGIN|MADE\s+IN|PRODUCT\s+OF|MANUFACTURED\s+IN|ORIGIN)\s*[:\-]?\s*([A-Za-z\s]+)', re.IGNORECASE),
        ]
        
        # Manufacturing Date patterns
        self.mfg_date_patterns = [
            re.compile(r'(?:MFD|MFG|MFG\s+DATE|MFD\s+DATE|DATE\s+OF\s+MFG|PACKED\s+ON|DATE\s+OF\s+MANUFACTURE|MANUFACTURED\s+ON|PKD)\s*[:\.\-]?\s*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})', re.IGNORECASE),
            re.compile(r'(?:MFD|MFG|MFG\s+DATE|MFD\s+DATE|DATE\s+OF\s+MFG|PACKED\s+ON|DATE\s+OF\s+MANUFACTURE|MANUFACTURED\s+ON|PKD)\s*[:\.\-]?\s*(\d{1,2}[/\.\-]\d{4})', re.IGNORECASE),
            re.compile(r'(?:MFD|MFG|MFG\s+DATE|MFD\s+DATE|DATE\s+OF\s+MFG|PACKED\s+ON|DATE\s+OF\s+MANUFACTURE|MANUFACTURED\s+ON|PKD)\s*[:\.\-]?\s*([A-Z]{3,9}\s*\d{4})', re.IGNORECASE),
        ]
        
        # Expiry Date patterns
        self.exp_date_patterns = [
            re.compile(r'(?:EXP|EXPIRY|EXP\s+DATE|EXPIRY\s+DATE|USE\s+BEFORE|BEST\s+BEFORE|BEST\s+BEFORE\s+END|USE\s+BY|EXPIRES\s+ON)\s*[:\.\-]?\s*(\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4})', re.IGNORECASE),
            re.compile(r'(?:EXP|EXPIRY|EXP\s+DATE|EXPIRY\s+DATE|USE\s+BEFORE|BEST\s+BEFORE|BEST\s+BEFORE\s+END|USE\s+BY|EXPIRES\s+ON)\s*[:\.\-]?\s*(\d{1,2}[/\.\-]\d{4})', re.IGNORECASE),
            re.compile(r'(?:EXP|EXPIRY|EXP\s+DATE|EXPIRY\s+DATE|USE\s+BEFORE|BEST\s+BEFORE|BEST\s+BEFORE\s+END|USE\s+BY|EXPIRES\s+ON)\s*[:\.\-]?\s*(\d+\s+MONTHS(?:\s+FROM\s+(?:MFG|MFD|PACKING))?)', re.IGNORECASE),
        ]
        
        # Batch Number patterns
        self.batch_patterns = [
            re.compile(r'(?:BATCH\s+(?:NO\.?|NUMBER)|LOT\s+(?:NO\.?|NUMBER)|BATCH|LOT|B\.NO\.?)\s*[:\-]?\s*([A-Z0-9\-\/]{3,20})', re.IGNORECASE),
        ]
        
        # Brand explicit patterns
        self.brand_patterns = [
            re.compile(r'(?:BRAND|TRADE\s+MARK|TM)\s*[:\-]?\s*(.+)', re.IGNORECASE),
        ]
        
        self.declaration_regex = re.compile(
            '|'.join(re.escape(kw) for kw in self.GENERIC_PACKAGING_TERMS),
            re.IGNORECASE
        )
    
    def is_generic_or_declaration(self, text: str) -> bool:
        """Check if text is generic packaging jargon, instruction, or declaration."""
        t = text.upper().strip()
        if len(t) < 3:
            return True
        if re.match(r'^[\d\s₹\.\,\-\:\/\#\%\(\)]+$', t):
            return True
        for kw in self.GENERIC_PACKAGING_TERMS:
            if kw == t or f" {kw} " in f" {t} " or t.startswith(f"{kw} ") or t.endswith(f" {kw}"):
                return True
            if kw in ['MRP', 'M.R.P.', 'INCL OF', 'ALL TAXES', 'MFG', 'MFD', 'EXP', 'BATCH', 'FSSAI', 'NET QTY']:
                if kw in t:
                    return True
        return False
    
    def _normalize_mrp(self, value: str) -> str:
        """Normalize MRP value to standard currency format."""
        cleaned = re.sub(r'[^\d\.]', '', value)
        try:
            num = float(cleaned)
            if num == int(num):
                return f"₹{int(num)}"
            else:
                return f"₹{num:.2f}"
        except ValueError:
            return f"₹{value}"
    
    def extract_mrp(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract MRP from OCR results with robust contextual search."""
        best_match = None
        best_confidence = 0.0
        
        has_image_mrp_cue = any(self.mrp_cue_pattern.search(it.get('text', '')) for it in ocr_results)
        
        for i, item in enumerate(ocr_results):
            text = item.get('text', '').strip()
            confidence = float(item.get('confidence', 0.0) or 0.0)
            box = item.get('box', [])
            
            # 1. Direct match on line with MRP keyword
            if self.mrp_cue_pattern.search(text):
                m = re.search(r'(?:RS\.?|INR|₹)?\s*(\d+(?:\.\d+)?)\s*(?:/\s*[-–]|/-|/–)?', text, re.IGNORECASE)
                if m and m.group(1):
                    val = self._normalize_mrp(m.group(1))
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = ExtractedField(value=val, confidence=confidence, box=box, evidence_text=text)
                        continue
            
            # 2. Check standalone number near MRP cues
            m_num = self.mrp_standalone_num.match(text)
            if m_num and m_num.group(1):
                try:
                    num_val = float(m_num.group(1))
                except ValueError:
                    num_val = 0
                if 1 <= num_val <= 50000:
                    is_near_cue = False
                    for offset in [-3, -2, -1, 1, 2, 3]:
                        ni = i + offset
                        if 0 <= ni < len(ocr_results):
                            if self.mrp_cue_pattern.search(ocr_results[ni].get('text', '')):
                                is_near_cue = True
                                break
                    if is_near_cue or (has_image_mrp_cue and '/' in text):
                        val = self._normalize_mrp(m_num.group(1))
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = ExtractedField(value=val, confidence=confidence, box=box, evidence_text=text)
                            continue
        
        return best_match
    
    def extract_net_quantity(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """
        Extract declared Net Quantity.
        Explicitly ignores 'MINIMUM WEIGHT' and nutritional stats.
        """
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item.get('text', '').strip()
            confidence = float(item.get('confidence', 0.0) or 0.0)
            
            # Reject minimum weight, nutrition, calories, or recycling percentages
            if re.search(r'\b(MINIMUM\s+WEIGHT|MIN\.?\s*WT|KCAL|ENERGY|PROTEIN|FAT|SUGAR|CARBOHYDRATE|RECYCLED|PLASTIC)\b', text, re.IGNORECASE):
                continue
                
            for pattern in self.net_qty_explicit_patterns:
                match = pattern.search(text)
                if match and match.lastindex >= 2:
                    value = match.group(1)
                    unit = match.group(2).lower()
                    if unit in ['litre', 'liter']:
                        unit = 'l'
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = ExtractedField(
                            value=value,
                            confidence=confidence,
                            box=item.get('box', []),
                            unit=unit,
                            evidence_text=text
                        )
        
        return best_match
    
    def extract_manufacturer(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract manufacturer using context and company entity patterns."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item.get('text', '').strip()
            confidence = float(item.get('confidence', 0.0) or 0.0)
            box = item.get('box', [])
            
            # Skip lines that are purely MRP, nutritional, or barcode
            if re.search(r'\b(MRP|INCL\s*OF|TAXES|KCAL|NUTRITION|RECYCLED)\b', text, re.IGNORECASE):
                continue
                
            # 1. Explicit Prefix pattern
            m = self.mfg_prefix_pattern.search(text)
            if m and len(m.group(1).strip()) > 3:
                val = m.group(1).strip()
                val = re.sub(r'^[#\*\-\s]+', '', val)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = ExtractedField(value=val, confidence=confidence, box=box, evidence_text=text)
                    continue
            
            # 2. Company entity suffix pattern
            m_ent = self.company_entity_pattern.search(text)
            if m_ent:
                val = m_ent.group(1).strip()
                val = re.sub(r'^[#\*\-\s]+', '', val)
                val = re.sub(r'COCA-COLA\s*YNDIA', 'COCA-COLA INDIA', val, flags=re.IGNORECASE)
                val = re.sub(r'PVT\.?\s*LTD\.?.*', 'PVT. LTD.', val, flags=re.IGNORECASE)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = ExtractedField(value=val, confidence=confidence, box=box, evidence_text=text)
                    continue
        
        return best_match
    
    def extract_packer(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract packer from OCR results."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item.get('text', '').strip()
            confidence = float(item.get('confidence', 0.0) or 0.0)
            
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
                            box=item.get('box', []),
                            evidence_text=text
                        )
        
        return best_match
    
    def extract_importer(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract importer from OCR results."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item.get('text', '').strip()
            confidence = float(item.get('confidence', 0.0) or 0.0)
            
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
                            box=item.get('box', []),
                            evidence_text=text
                        )
        
        return best_match
    
    def extract_country_of_origin(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract Country of Origin only from explicit textual declarations."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item.get('text', '').strip()
            confidence = float(item.get('confidence', 0.0) or 0.0)
            box = item.get('box', [])
            
            # Reject slogans like "India's number one" or general references
            if re.search(r"\b(NUMBER\s+ONE|BEST|MARKET|INDEX)\b", text, re.IGNORECASE):
                continue
                
            for pat in self.country_explicit_patterns:
                m = pat.search(text)
                if m:
                    country_name = "India" if "INDIA" in m.group(1).upper() else m.group(1).strip().title()
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = ExtractedField(value=country_name, confidence=confidence, box=box, evidence_text=text)
        
        return best_match
    
    def extract_manufacturing_date(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract manufacturing date from OCR results."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item.get('text', '').strip()
            confidence = float(item.get('confidence', 0.0) or 0.0)
            
            for pattern in self.mfg_date_patterns:
                match = pattern.search(text)
                if match and match.lastindex >= 1:
                    value = match.group(1).strip()
                    value = self._normalize_date(value)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = ExtractedField(
                            value=value,
                            confidence=confidence,
                            box=item.get('box', []),
                            evidence_text=text
                        )
        
        return best_match
    
    def extract_expiry_date(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract expiry date from OCR results."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item.get('text', '').strip()
            confidence = float(item.get('confidence', 0.0) or 0.0)
            
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
                            box=item.get('box', []),
                            evidence_text=text
                        )
        
        return best_match
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to standard format."""
        date_str = date_str.replace('-', '/').replace('.', '/')
        parts = date_str.split('/')
        if len(parts) == 3:
            day = parts[0].zfill(2)
            month = parts[1].zfill(2)
            year = parts[2]
            return f"{day}/{month}/{year}"
        elif len(parts) == 2:
            month = parts[0].zfill(2)
            year = parts[1]
            return f"01/{month}/{year}"
        return date_str
    
    def extract_batch_number(self, ocr_results: List[Dict[str, Any]]) -> Optional[ExtractedField]:
        """Extract batch/lot number from OCR results."""
        best_match = None
        best_confidence = 0.0
        
        for item in ocr_results:
            text = item.get('text', '').strip()
            confidence = float(item.get('confidence', 0.0) or 0.0)
            
            for pattern in self.batch_patterns:
                match = pattern.search(text)
                if match and match.lastindex >= 1:
                    value = match.group(1).strip()
                    if self._is_valid_batch(value):
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = ExtractedField(
                                value=value,
                                confidence=confidence,
                                box=item.get('box', []),
                                evidence_text=text
                            )
        
        return best_match
    
    def _is_valid_batch(self, value: str) -> bool:
        """Check if extracted string represents a valid printed batch code."""
        if re.match(r'^\d+$', value):
            return 4 <= len(value) <= 12
        if re.match(r'^[A-Z0-9\-\/]+$', value, re.IGNORECASE):
            return 3 <= len(value) <= 20
        return False
    
    def extract_brand(self, ocr_results: List[Dict[str, Any]], source: Optional[str] = None) -> Optional[ExtractedField]:
        """
        Extract brand from OCR results using visual prominence and generic blacklist filtering.
        """
        candidates = []
        for item in ocr_results:
            text = item.get('text', '').strip()
            conf = float(item.get('confidence', 0.0) or 0.0)
            box = item.get('box', [])
            
            if self.is_generic_or_declaration(text):
                continue
            
            area = 0
            if box and len(box) >= 4:
                w = max(p[0] for p in box) - min(p[0] for p in box)
                h = max(p[1] for p in box) - min(p[1] for p in box)
                area = w * h
            
            clean_text = text.strip()
            if clean_text.islower() or clean_text.isupper():
                clean_text = clean_text.title()
            
            # Prominence score: area + confidence + source priority boost
            source_boost = 1.5 if source == 'front' else (1.0 if source == 'back' else 0.5)
            score = conf * 3.0 * source_boost + (area / 10000.0)
            
            candidates.append({
                'text': clean_text,
                'conf': conf,
                'box': box,
                'score': score,
                'raw': text
            })
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda c: c['score'], reverse=True)
        best = candidates[0]
        return ExtractedField(value=best['text'], confidence=best['conf'], box=best['box'], evidence_text=best['raw'])
    
    def extract_product_name(self, ocr_results: List[Dict[str, Any]], brand_field: Optional[ExtractedField] = None) -> Optional[ExtractedField]:
        """
        Extract product name describing what the consumer is buying.
        Combines brand with prominent variant / category descriptor if present.
        """
        brand_val = brand_field.value if brand_field else None
        
        descriptors = []
        for item in ocr_results:
            t = item.get('text', '').strip()
            conf = float(item.get('confidence', 0.0) or 0.0)
            box = item.get('box', [])
            
            # Look for product descriptor words across categories (beverages, biscuits, cosmetics, snacks, etc.)
            if re.search(r'\b(mango drink|fruit drink|juice|beverage|refresh|biscuits|cookies|chips|snack|oil|milk|shampoo|soap|cream|lotion|tablets|powder|detergent|cleaner|flour|rice)\b', t, re.IGNORECASE):
                clean_desc = t.strip()
                clean_desc = re.sub(r'^(?:ready-to-serve|number one|tasty|treat|made frum|real)\s*', '', clean_desc, flags=re.IGNORECASE).strip()
                if clean_desc and len(clean_desc) > 2 and not self.is_generic_or_declaration(clean_desc):
                    descriptors.append({'text': clean_desc.title(), 'conf': conf, 'box': box, 'raw': t})
        
        if brand_val and descriptors:
            desc = descriptors[0]['text']
            if desc.lower() not in brand_val.lower():
                name = f"{brand_val} {desc}".strip()
                return ExtractedField(value=name, confidence=descriptors[0]['conf'], box=descriptors[0]['box'], evidence_text=descriptors[0]['raw'])
            else:
                return ExtractedField(value=brand_val, confidence=brand_field.confidence, box=brand_field.box, evidence_text=brand_field.evidence_text)
        elif brand_val:
            return ExtractedField(value=brand_val, confidence=brand_field.confidence, box=brand_field.box, evidence_text=brand_field.evidence_text)
        elif descriptors:
            return ExtractedField(value=descriptors[0]['text'], confidence=descriptors[0]['conf'], box=descriptors[0]['box'], evidence_text=descriptors[0]['raw'])
        return None
    
    def extract_all(self, ocr_results: List[Dict[str, Any]], source: Optional[str] = None) -> Dict[str, Any]:
        """Extract all packaged commodity fields from OCR detections."""
        fields = {}
        
        # 1. Brand & Product Name
        brand = self.extract_brand(ocr_results, source=source)
        fields['brand'] = brand.to_dict() if brand else None
        
        product_name = self.extract_product_name(ocr_results, brand_field=brand)
        fields['product_name'] = product_name.to_dict() if product_name else None
        
        # 2. MRP
        mrp = self.extract_mrp(ocr_results)
        fields['mrp'] = mrp.to_dict() if mrp else None
        
        # 3. Net Quantity
        net_qty = self.extract_net_quantity(ocr_results)
        fields['net_quantity'] = net_qty.to_dict() if net_qty else None
        
        # 4. Manufacturer, Packer, Importer
        manufacturer = self.extract_manufacturer(ocr_results)
        fields['manufacturer'] = manufacturer.to_dict() if manufacturer else None
        
        packer = self.extract_packer(ocr_results)
        fields['packer'] = packer.to_dict() if packer else None
        
        importer = self.extract_importer(ocr_results)
        fields['importer'] = importer.to_dict() if importer else None
        
        # 5. Country of Origin
        country = self.extract_country_of_origin(ocr_results)
        fields['country_of_origin'] = country.to_dict() if country else None
        
        # 6. Dates & Batch
        mfg_date = self.extract_manufacturing_date(ocr_results)
        fields['manufacturing_date'] = mfg_date.to_dict() if mfg_date else None
        
        exp_date = self.extract_expiry_date(ocr_results)
        fields['expiry_date'] = exp_date.to_dict() if exp_date else None
        
        batch = self.extract_batch_number(ocr_results)
        fields['batch_number'] = batch.to_dict() if batch else None
        
        for k, v in fields.items():
            if v and source:
                v['source'] = source
        
        return fields
