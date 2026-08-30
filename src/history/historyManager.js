/**
 * Inspection History & Same-Product Comparison Engine
 * Member 5 - Offline Database + Sync + Voice + Testing Engineer
 * 
 * Supports fast local querying, filtering, and cross-inspection comparison for Legal Metrology violations.
 */

import {
  getAllInspections,
  getPendingInspections as idbGetPending,
  getInspectionsByStatus,
  getInspectionById as idbGetById,
  getInspectionsByProduct,
  SYNC_STATUS
} from '../db/indexedDB.js';

/**
 * Get inspection history with filtering, sorting, and pagination
 * @param {Object} options { status, category, search, limit, offset, sortBy }
 * @returns {Promise<{items: Array<Object>, total: number}>}
 */
export async function getInspectionHistory(options = {}) {
  let records = await getAllInspections();

  // 1. Filter by sync status ('pending' | 'synced' | 'failed')
  if (options.status) {
    records = records.filter(r => r.sync_status === options.status);
  }

  // 2. Filter by category
  if (options.category && options.category !== 'ALL') {
    records = records.filter(r => (r.category || '').toLowerCase() === options.category.toLowerCase());
  }

  // 3. Filter by compliance status
  if (options.compliance_status) {
    records = records.filter(r => r.compliance_status === options.compliance_status);
  }

  // 4. Free text search (product name, brand, barcode, inspection_id)
  if (options.search) {
    const q = options.search.toLowerCase().trim();
    records = records.filter(r => 
      (r.product_name && r.product_name.toLowerCase().includes(q)) ||
      (r.inspection_id && r.inspection_id.toLowerCase().includes(q)) ||
      (r.barcode && r.barcode.includes(q)) ||
      (r.category && r.category.toLowerCase().includes(q))
    );
  }

  // 5. Sorting
  const sortBy = options.sortBy || 'created_at_desc';
  if (sortBy === 'created_at_desc') {
    records.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  } else if (sortBy === 'created_at_asc') {
    records.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  } else if (sortBy === 'mrp_desc') {
    records.sort((a, b) => (Number(b.mrp) || 0) - (Number(a.mrp) || 0));
  }

  const total = records.length;
  const offset = options.offset || 0;
  const limit = options.limit || 50;
  const paginated = records.slice(offset, offset + limit);

  return {
    items: paginated,
    total
  };
}

/**
 * Get all pending inspections awaiting synchronization
 * @returns {Promise<Array<Object>>}
 */
export async function getPendingInspections() {
  return await idbGetPending();
}

/**
 * Get all synced inspections
 * @returns {Promise<Array<Object>>}
 */
export async function getSyncedInspections() {
  return await getInspectionsByStatus(SYNC_STATUS.SYNCED);
}

/**
 * Get single inspection by ID
 * @param {string} id 
 * @returns {Promise<Object|null>}
 */
export async function getInspectionById(id) {
  return await idbGetById(id);
}

/**
 * Parse numeric quantity and unit from string (e.g. "100 g", "500 ml", "1.5 kg")
 * @param {string} netQtyStr 
 * @returns {{value: number, unit: string}|null}
 */
function parseQuantity(netQtyStr) {
  if (!netQtyStr || typeof netQtyStr !== 'string') return null;
  const match = netQtyStr.trim().match(/([\d.]+)\s*([a-zA-Z]+)/);
  if (!match) return null;
  
  let val = parseFloat(match[1]);
  let unit = match[2].toLowerCase();

  // Normalize units to grams or milliliters
  if (unit === 'kg') {
    val *= 1000;
    unit = 'g';
  } else if (unit === 'l' || unit === 'ltr' || unit === 'liter' || unit === 'liters') {
    val *= 1000;
    unit = 'ml';
  }

  return { value: val, unit };
}

/**
 * Same-Product Comparison Engine
 * Compares current inspection against historical inspections of the same product.
 * Detects:
 *  - MRP changes / Price hikes
 *  - Shrinkflation (Net quantity reduction at same or higher price)
 *  - Unit sale price inflation
 *  - Address / Manufacturer tampering
 * 
 * @param {Object} currentInspection 
 * @returns {Promise<{
 *   hasHistory: boolean,
 *   previousScansCount: number,
 *   latestPrevious: Object|null,
 *   changesDetected: Array<string>,
 *   shrinkflationDetected: boolean,
 *   priceHikeDetected: boolean,
 *   comparisonDetails: Object
 * }>}
 */
export async function compareProductWithPrevious(currentInspection) {
  if (!currentInspection || !currentInspection.product_name) {
    return { hasHistory: false, previousScansCount: 0, changesDetected: [] };
  }

  const allPrevious = await getInspectionsByProduct(currentInspection.product_name);
  
  // Filter out the current inspection itself
  const historical = allPrevious.filter(i => i.inspection_id !== currentInspection.inspection_id);

  if (historical.length === 0) {
    return {
      hasHistory: false,
      previousScansCount: 0,
      latestPrevious: null,
      changesDetected: [],
      shrinkflationDetected: false,
      priceHikeDetected: false,
      comparisonDetails: {}
    };
  }

  // Get most recent previous scan
  const previous = historical[0];
  const changes = [];
  let shrinkflation = false;
  let priceHike = false;

  const currentMrp = Number(currentInspection.mrp) || null;
  const prevMrp = Number(previous.mrp) || null;

  const currentQty = parseQuantity(currentInspection.net_quantity);
  const prevQty = parseQuantity(previous.net_quantity);

  // 1. MRP Change Detection
  if (currentMrp !== null && prevMrp !== null && currentMrp !== prevMrp) {
    const diff = currentMrp - prevMrp;
    const sign = diff > 0 ? '+' : '';
    changes.push(`MRP changed from ₹${prevMrp} to ₹${currentMrp} (${sign}₹${diff.toFixed(2)})`);
    if (diff > 0) priceHike = true;
  }

  // 2. Shrinkflation Detection (Quantity reduced)
  if (currentQty && prevQty && currentQty.unit === prevQty.unit) {
    if (currentQty.value < prevQty.value) {
      shrinkflation = true;
      const reduction = prevQty.value - currentQty.value;
      changes.push(`Shrinkflation Alert: Net quantity decreased from ${previous.net_quantity} to ${currentInspection.net_quantity} (-${reduction}${currentQty.unit})`);
    } else if (currentQty.value > prevQty.value) {
      changes.push(`Net quantity increased from ${previous.net_quantity} to ${currentInspection.net_quantity}`);
    }
  }

  // 3. Manufacturer / Address change
  if (currentInspection.manufacturer && previous.manufacturer && currentInspection.manufacturer !== previous.manufacturer) {
    changes.push(`Manufacturer / Address updated from "${previous.manufacturer}" to "${currentInspection.manufacturer}"`);
  }

  return {
    hasHistory: true,
    previousScansCount: historical.length,
    latestPrevious: previous,
    changesDetected: changes,
    shrinkflationDetected: shrinkflation,
    priceHikeDetected: priceHike,
    comparisonDetails: {
      current: {
        inspection_id: currentInspection.inspection_id,
        mrp: currentInspection.mrp,
        net_quantity: currentInspection.net_quantity,
        unit_sale_price: currentInspection.unit_sale_price,
        created_at: currentInspection.created_at
      },
      previous: {
        inspection_id: previous.inspection_id,
        mrp: previous.mrp,
        net_quantity: previous.net_quantity,
        unit_sale_price: previous.unit_sale_price,
        created_at: previous.created_at
      }
    }
  };
}

/**
 * Calculate dashboard overview metrics
 * @returns {Promise<Object>}
 */
export async function getDashboardMetrics() {
  const records = await getAllInspections();
  const total = records.length;
  
  const compliantCount = records.filter(r => r.compliance_status === 'COMPLIANT').length;
  const violationCount = records.filter(r => r.compliance_status === 'NON_COMPLIANT').length;
  const reviewCount = records.filter(r => r.compliance_status === 'FLAGGED_MANUAL_REVIEW').length;
  const pendingCount = records.filter(r => r.sync_status === SYNC_STATUS.PENDING).length;
  const syncedCount = records.filter(r => r.sync_status === SYNC_STATUS.SYNCED).length;
  const failedCount = records.filter(r => r.sync_status === SYNC_STATUS.FAILED).length;

  const complianceRate = total > 0 ? ((compliantCount / total) * 100).toFixed(1) : '100.0';

  // Category breakdown
  const categoryMap = {};
  records.forEach(r => {
    const cat = r.category || 'General Commodities';
    categoryMap[cat] = (categoryMap[cat] || 0) + 1;
  });

  return {
    total,
    compliantCount,
    violationCount,
    reviewCount,
    pendingCount,
    syncedCount,
    failedCount,
    complianceRate: Number(complianceRate),
    categoryMap
  };
}

/**
 * Export all or filtered inspection records as formatted CSV
 * @param {Array<Object>} records - Array of inspection records
 * @returns {string} CSV string content
 */
export function exportInspectionsAsCSV(records) {
  if (!records || records.length === 0) {
    return 'Inspection ID,Product Name,Category,MRP,Net Quantity,Unit Sale Price,Manufacturer,Compliance Status,Violations Count,Sync Status,Officer Reviewed,Created At\n';
  }

  const headers = [
    'Inspection ID',
    'Product Name',
    'Category',
    'MRP (INR)',
    'Net Quantity',
    'Unit Sale Price',
    'Manufacturer',
    'Compliance Status',
    'Violations Count',
    'Sync Status',
    'Officer Reviewed',
    'Reviewer ID',
    'Created At'
  ];

  const escapeCSV = (val) => {
    if (val === null || val === undefined) return '""';
    const str = String(val).replace(/"/g, '""');
    return `"${str}"`;
  };

  const rows = records.map(r => {
    const violCount = Array.isArray(r.violations) ? r.violations.length : 0;
    return [
      escapeCSV(r.inspection_id),
      escapeCSV(r.product_name),
      escapeCSV(r.category),
      escapeCSV(r.mrp),
      escapeCSV(r.net_quantity),
      escapeCSV(r.unit_sale_price),
      escapeCSV(r.manufacturer),
      escapeCSV(r.compliance_status),
      escapeCSV(violCount),
      escapeCSV(r.sync_status),
      escapeCSV(r.officer_reviewed ? 'YES' : 'NO'),
      escapeCSV(r.reviewer_id || 'N/A'),
      escapeCSV(r.created_at)
    ].join(',');
  });

  return [headers.join(','), ...rows].join('\n');
}

/**
 * Generate formatted HTML Legal Metrology Rule 6 Enforcement Notice
 * @param {Object} inspection - Single inspection record
 * @returns {string} Printable HTML string
 */
export function generateStatutoryNoticeHTML(inspection) {
  const violations = inspection.violations || [];
  const officerId = inspection.reviewer_id || 'OFFICER-007';
  const inspectedDate = new Date(inspection.created_at || Date.now()).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'
  });

  const violationsRows = violations.length > 0 
    ? violations.map((v, i) => `
        <tr>
          <td style="padding: 8px; border: 1px solid #333; text-align: center;">${i + 1}</td>
          <td style="padding: 8px; border: 1px solid #333; font-weight: bold; color: #b91c1c;">${v.rule_id || 'RULE-DEF-001'}</td>
          <td style="padding: 8px; border: 1px solid #333;">${v.field || 'Mandatory Declaration'}</td>
          <td style="padding: 8px; border: 1px solid #333;">${v.requirement || v.message || 'Mandatory statutory declaration missing or non-compliant under Legal Metrology Rules 2011'}</td>
          <td style="padding: 8px; border: 1px solid #333; color: #b91c1c; font-weight: bold;">NON-COMPLIANT</td>
        </tr>
      `).join('')
    : `<tr><td colspan="5" style="padding: 12px; text-align: center; color: #15803d; border: 1px solid #333;">No statutory violations detected. All declarations comply with Legal Metrology Rules, 2011.</td></tr>`;

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Statutory Enforcement Notice - ${inspection.inspection_id}</title>
  <style>
    @media print {
      body { margin: 0; padding: 20px; font-size: 12pt; color: #000; background: #fff; }
      .no-print { display: none !important; }
      .notice-container { border: 2px solid #000 !important; box-shadow: none !important; }
    }
    body { font-family: 'Times New Roman', serif; margin: 20px auto; max-width: 800px; color: #111; line-height: 1.4; }
    .notice-container { border: 2px solid #222; padding: 30px 40px; background: #fff; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .header { text-align: center; border-bottom: 2px solid #000; padding-bottom: 15px; margin-bottom: 20px; }
    .header h2 { margin: 0 0 4px 0; font-size: 1.3rem; text-transform: uppercase; letter-spacing: 0.5px; }
    .header h3 { margin: 0 0 4px 0; font-size: 1.05rem; font-weight: normal; }
    .header p { margin: 0; font-size: 0.85rem; font-style: italic; color: #444; }
    .meta-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.9rem; }
    .meta-table td { padding: 5px 8px; }
    .meta-table td.label { font-weight: bold; width: 25%; color: #333; }
    .violations-table { width: 100%; border-collapse: collapse; margin: 15px 0 25px 0; font-size: 0.85rem; }
    .violations-table th { background: #f3f4f6; border: 1px solid #333; padding: 8px; font-size: 0.8rem; text-transform: uppercase; text-align: left; }
    .legal-text { font-size: 0.85rem; text-align: justify; margin-bottom: 25px; line-height: 1.5; }
    .signatures { display: flex; justify-content: space-between; margin-top: 50px; font-size: 0.9rem; }
    .sig-box { text-align: center; width: 220px; border-top: 1px solid #333; padding-top: 6px; }
    .btn-bar { display: flex; justify-content: space-between; margin-bottom: 20px; }
    .btn { padding: 8px 16px; background: #0284c7; color: #fff; border: none; border-radius: 4px; font-family: sans-serif; cursor: pointer; font-size: 0.9rem; }
    .btn-print { background: #15803d; }
  </style>
</head>
<body>
  <div class="btn-bar no-print">
    <button class="btn btn-print" onclick="window.print()">🖨️ Print / Save as PDF Notice</button>
    <button class="btn" onclick="window.close()">Close Window</button>
  </div>

  <div class="notice-container">
    <div class="header">
      <h2>Government of India</h2>
      <h3>Department of Consumer Affairs • Legal Metrology Division</h3>
      <p>Inspection & Compliance Notice issued under Rule 6, Legal Metrology (Packaged Commodities) Rules, 2011</p>
    </div>

    <table class="meta-table">
      <tr>
        <td class="label">Notice Ref / Inspection ID:</td>
        <td><strong>${inspection.inspection_id}</strong></td>
        <td class="label">Date & Time of Audit:</td>
        <td>${inspectedDate}</td>
      </tr>
      <tr>
        <td class="label">Commodity / Product:</td>
        <td><strong>${inspection.product_name || 'Packaged Commodity'}</strong></td>
        <td class="label">Category:</td>
        <td>${inspection.category || 'General'}</td>
      </tr>
      <tr>
        <td class="label">Declared MRP:</td>
        <td>₹${inspection.mrp || 'N/A'}</td>
        <td class="label">Declared Net Quantity:</td>
        <td>${inspection.net_quantity || 'N/A'}</td>
      </tr>
      <tr>
        <td class="label">Manufacturer / Packer:</td>
        <td colspan="3">${inspection.manufacturer || 'Name & Address not clearly declared'}</td>
      </tr>
      <tr>
        <td class="label">Inspection Status:</td>
        <td colspan="3"><strong style="color: ${inspection.compliance_status === 'COMPLIANT' ? '#15803d' : '#b91c1c'};">${inspection.compliance_status}</strong></td>
      </tr>
    </table>

    <h4 style="margin: 15px 0 6px 0; text-transform: uppercase; font-size: 0.9rem; border-bottom: 1px solid #999; padding-bottom: 4px;">
      Schedule of Declarations & Statutory Findings
    </h4>

    <table class="violations-table">
      <thead>
        <tr>
          <th style="width: 5%; text-align: center;">#</th>
          <th style="width: 20%;">Rule Citation</th>
          <th style="width: 25%;">Mandatory Field</th>
          <th>Statutory Requirement / Scan Finding</th>
          <th style="width: 15%;">Result</th>
        </tr>
      </thead>
      <tbody>
        ${violationsRows}
      </tbody>
    </table>

    <div class="legal-text">
      <strong>STATUTORY DIRECTIVE:</strong>
      WHEREAS an inspection of the above-mentioned pre-packaged commodity was conducted using the AI-assisted LegalMetrix inspection platform in accordance with the standards specified under the Legal Metrology Act, 2009 and the Legal Metrology (Packaged Commodities) Rules, 2011.
      <br/><br/>
      ${violations.length > 0 
        ? 'TAKE NOTICE that the package fails to satisfy the mandatory declarations stipulated under the Act/Rules. You are hereby called upon to show cause within 15 (fifteen) days from the receipt of this notice why penal action under Section 36 of the Legal Metrology Act, 2009 should not be initiated against you.'
        : 'The scanned sample conforms with the mandatory declaration requirements under Rule 6 of the Legal Metrology (Packaged Commodities) Rules, 2011 as on the date of inspection.'}
    </div>

    <div class="signatures">
      <div class="sig-box">
        Signature of Authorized Retailer / Packer
      </div>
      <div class="sig-box">
        <strong>Inspector / Enforcement Officer</strong><br/>
        ID: ${officerId}<br/>
        Legal Metrology Department
      </div>
    </div>
  </div>
</body>
</html>
`;
}
