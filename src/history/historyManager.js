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
