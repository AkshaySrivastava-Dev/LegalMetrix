/**
 * SQLite / Edge Backend Sync Client (Adapted to Authoritative POST /api/sync)
 * Member 5 - Offline Database + Sync + Voice + Testing Engineer
 * 
 * Synchronizes client-side IndexedDB records with the authoritative backend SQLite database via FastAPI.
 * Guarantees idempotent upsert, exact schema mapping, and offline resilience.
 */

const DEFAULT_CONFIG = {
  apiBaseUrl: (typeof process !== 'undefined' && process.env?.VITE_API_URL) ||
              (typeof window !== 'undefined' && window.__API_URL) ||
              'http://localhost:8000',
  syncEndpoint: '/api/sync',
  batchEndpoint: '/api/sync',
  mockMode: false // When backend server is offline or in disconnected demo mode
};

let activeConfig = { ...DEFAULT_CONFIG };

/**
 * Configure SQLite backend API options
 * @param {Object} options { apiBaseUrl, mockMode }
 */
export function configureSQLiteBackend(options = {}) {
  activeConfig = { ...activeConfig, ...options };
  console.log('[SQLiteClient] Configured API Base:', activeConfig.apiBaseUrl, 'MockMode:', activeConfig.mockMode);
}

/**
 * Format local IndexedDB record to backend expected record schema
 * @param {Object} inspection 
 * @returns {Object}
 */
export function formatInspectionForBackend(inspection) {
  // Resolve checks: direct checks -> raw_payload.checks -> mandatory_declarations fallback
  const checksData = inspection.checks !== undefined
    ? inspection.checks
    : (inspection.raw_payload?.checks !== undefined
        ? inspection.raw_payload.checks
        : (inspection.mandatory_declarations || {}));

  // Resolve violations
  const violationsData = inspection.violations !== undefined
    ? inspection.violations
    : (inspection.raw_payload?.violations || []);

  // Resolve evidence
  const evidenceData = inspection.evidence !== undefined
    ? inspection.evidence
    : (inspection.raw_payload?.evidence || {});

  return {
    inspection_id: inspection.inspection_id,
    product_name: inspection.product_name || 'Unknown Commodity',
    brand: inspection.brand || inspection.raw_payload?.brand || inspection.manufacturer || '',
    category: inspection.category || 'General Commodities',
    variant: inspection.variant || inspection.raw_payload?.variant || '',
    mrp: inspection.mrp !== null && inspection.mrp !== undefined ? String(inspection.mrp) : '',
    net_quantity: inspection.net_quantity || '',
    manufacturer: inspection.manufacturer || '',
    confidence: typeof inspection.confidence === 'number' ? Number(inspection.confidence.toFixed(3)) : 0.950,
    compliance_status: inspection.compliance_status || inspection.result || 'COMPLIANT',
    violations: typeof violationsData === 'string' ? violationsData : JSON.stringify(violationsData),
    checks: typeof checksData === 'string' ? checksData : JSON.stringify(checksData),
    evidence: typeof evidenceData === 'string' ? evidenceData : JSON.stringify(evidenceData),
    source: inspection.source || inspection.raw_payload?.source || 'mobile_offline',
    created_at: inspection.created_at || new Date().toISOString(),
    sync_status: inspection.sync_status || 'pending'
  };
}

// Alias for backwards compatibility
export const formatInspectionForSQLite = formatInspectionForBackend;

/**
 * Upload single inspection to POST /api/sync
 * @param {Object} inspection Local inspection record from IndexedDB
 * @returns {Promise<{success: boolean, data?: any, error?: string}>}
 */
export async function uploadInspectionToSQLite(inspection) {
  if (activeConfig.mockMode) {
    // Simulated local edge persistence delay
    await new Promise(r => setTimeout(r, 100));
    console.log(`[SQLite Mock] Inspection persisted: ${inspection.inspection_id}`);
    return {
      success: true,
      data: {
        inspection_id: inspection.inspection_id,
        status: 'synced',
        action: 'created',
        reason: 'Mock synchronized'
      }
    };
  }

  const record = formatInspectionForBackend(inspection);
  const targetUrl = `${activeConfig.apiBaseUrl}${activeConfig.syncEndpoint}`;

  try {
    const response = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ records: [record] })
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Sync HTTP error (${response.status}): ${errText}`);
    }

    const data = await response.json();
    
    // Find result for the matching inspection_id
    const itemResult = data.results?.find(r => r.inspection_id === inspection.inspection_id) || data.results?.[0];

    if (itemResult && itemResult.status === 'synced') {
      console.log(`[SQLiteClient] Inspection [${inspection.inspection_id}] successfully synchronized.`);
      return { success: true, data: itemResult };
    } else {
      const failReason = itemResult?.reason || 'Sync rejected by backend';
      console.warn(`[SQLiteClient] Inspection [${inspection.inspection_id}] sync failed: ${failReason}`);
      return { success: false, error: failReason };
    }
  } catch (err) {
    console.warn(`[SQLiteClient] Could not reach sync endpoint at ${targetUrl}:`, err.message);
    return { success: false, error: err.message };
  }
}

/**
 * Batch upload multiple inspections to POST /api/sync
 * @param {Array<Object>} inspections 
 * @returns {Promise<{syncedCount: number, failedCount: number, results: Array}>}
 */
export async function batchUploadToSQLite(inspections) {
  if (!inspections || inspections.length === 0) {
    return { syncedCount: 0, failedCount: 0, results: [] };
  }

  if (activeConfig.mockMode) {
    await new Promise(r => setTimeout(r, 100));
    return {
      syncedCount: inspections.length,
      failedCount: 0,
      results: inspections.map(i => ({ inspection_id: i.inspection_id, status: 'synced' }))
    };
  }

  const records = inspections.map(formatInspectionForBackend);
  const targetUrl = `${activeConfig.apiBaseUrl}${activeConfig.batchEndpoint}`;

  try {
    const response = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ records })
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Batch sync HTTP error (${response.status}): ${errText}`);
    }

    const data = await response.json();
    const results = data.results || [];
    const syncedCount = data.synced_count ?? results.filter(r => r.status === 'synced').length;
    const failedCount = data.failed_count ?? results.filter(r => r.status !== 'synced').length;

    return { syncedCount, failedCount, results };
  } catch (err) {
    console.error(`[SQLiteClient] Batch sync error at ${targetUrl}:`, err);
    return {
      syncedCount: 0,
      failedCount: inspections.length,
      results: inspections.map(i => ({ inspection_id: i.inspection_id, status: 'failed', error: err.message }))
    };
  }
}
