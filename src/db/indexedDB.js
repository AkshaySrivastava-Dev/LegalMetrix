/**
 * Legal Metrology Offline Database (IndexedDB)
 * Member 5 - Offline Database + Sync + Voice + Testing Engineer
 * 
 * Zero-dependency, Promise-based IndexedDB implementation designed for rural/low-connectivity environments.
 * Ensures the inspection pipeline never stalls when offline.
 */

const DB_NAME = 'LegalMetrologyDB';
const DB_VERSION = 1;

export const STORES = {
  INSPECTIONS: 'inspections',
  SYNC_LOG: 'sync_log',
  OFFLINE_CACHE: 'offline_cache'
};

export const SYNC_STATUS = {
  PENDING: 'pending',
  SYNCED: 'synced',
  FAILED: 'failed',
  SYNCING: 'syncing'
};

export const COMPLIANCE_RESULT = {
  COMPLIANT: 'COMPLIANT',
  NON_COMPLIANT: 'NON_COMPLIANT',
  FLAGGED_MANUAL_REVIEW: 'FLAGGED_MANUAL_REVIEW',
  UNCLEAR_IMAGE: 'UNCLEAR_IMAGE'
};

let dbInstance = null;

/**
 * Initialize and open IndexedDB database
 * @returns {Promise<IDBDatabase>}
 */
export function initDB() {
  if (dbInstance) {
    return Promise.resolve(dbInstance);
  }

  return new Promise((resolve, reject) => {
    // Check IndexedDB availability
    const indexedDBObj = typeof window !== 'undefined' ? (window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB) : null;
    
    if (!indexedDBObj) {
      const err = new Error('IndexedDB is not supported in this environment');
      console.error('[IndexedDB]', err);
      return reject(err);
    }

    const request = indexedDBObj.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      // 1. Primary Store: Inspections
      if (!db.objectStoreNames.contains(STORES.INSPECTIONS)) {
        const inspectionStore = db.createObjectStore(STORES.INSPECTIONS, {
          keyPath: 'inspection_id'
        });

        // Query Indexes
        inspectionStore.createIndex('sync_status', 'sync_status', { unique: false });
        inspectionStore.createIndex('timestamp', 'timestamp', { unique: false });
        inspectionStore.createIndex('category', 'category', { unique: false });
        inspectionStore.createIndex('product_name', 'product_name', { unique: false });
        inspectionStore.createIndex('compliance_status', 'compliance_status', { unique: false });
        inspectionStore.createIndex('created_at', 'created_at', { unique: false });
      }

      // 2. Audit / Sync Log Store
      if (!db.objectStoreNames.contains(STORES.SYNC_LOG)) {
        const logStore = db.createObjectStore(STORES.SYNC_LOG, {
          keyPath: 'id',
          autoIncrement: true
        });
        logStore.createIndex('inspection_id', 'inspection_id', { unique: false });
        logStore.createIndex('timestamp', 'timestamp', { unique: false });
      }

      // 3. Offline Cache Store (for pre-recorded 360 videos, sample templates, offline rules)
      if (!db.objectStoreNames.contains(STORES.OFFLINE_CACHE)) {
        db.createObjectStore(STORES.OFFLINE_CACHE, { keyPath: 'key' });
      }

      console.log('[IndexedDB] Database schema created/upgraded successfully.');
    };

    request.onsuccess = (event) => {
      dbInstance = event.target.result;
      console.log('[IndexedDB] Database initialized successfully:', DB_NAME, 'v' + DB_VERSION);
      resolve(dbInstance);
    };

    request.onerror = (event) => {
      console.error('[IndexedDB] Error opening database:', event.target.error);
      reject(event.target.error);
    };
  });
}

/**
 * Generate a unique inspection ID
 * Format: INSP-YYYYMMDD-XXXXXX (e.g. INSP-20260829-9A3F1B)
 */
export function generateInspectionId() {
  const now = new Date();
  const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '');
  const randomHex = Math.random().toString(16).substring(2, 8).toUpperCase();
  return `INSP-${dateStr}-${randomHex}`;
}

/**
 * Save or update an inspection in local IndexedDB
 * @param {Object} inspectionData 
 * @returns {Promise<Object>} The saved inspection object
 */
export async function saveInspection(inspectionData) {
  const db = await initDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORES.INSPECTIONS], 'readwrite');
    const store = transaction.objectStore(STORES.INSPECTIONS);

    // Normalize inspection structure
    const now = new Date().toISOString();
    const inspectionId = inspectionData.inspection_id || generateInspectionId();

    const record = {
      inspection_id: inspectionId,
      product_name: inspectionData.product_name || 'Unknown Packaged Good',
      category: inspectionData.category || 'General Commodities',
      barcode: inspectionData.barcode || null,
      mrp: inspectionData.mrp || null,
      net_quantity: inspectionData.net_quantity || null,
      unit_sale_price: inspectionData.unit_sale_price || null,
      mfg_date: inspectionData.mfg_date || null,
      expiry_date: inspectionData.expiry_date || null,
      manufacturer: inspectionData.manufacturer || null,
      consumer_care: inspectionData.consumer_care || null,
      country_of_origin: inspectionData.country_of_origin || 'India',
      
      // Compliance & AI OCR Results
      compliance_status: inspectionData.compliance_status || COMPLIANCE_RESULT.COMPLIANT,
      confidence: typeof inspectionData.confidence === 'number' ? inspectionData.confidence : 0.95,
      violations: Array.isArray(inspectionData.violations) ? inspectionData.violations : [],
      mandatory_declarations: inspectionData.mandatory_declarations || {
        mrp_present: true,
        net_qty_present: true,
        mfg_date_present: true,
        consumer_care_present: true,
        mfg_address_present: true,
        unit_sale_price_present: true,
        country_of_origin_present: true
      },

      // Evidence (Images, Video frames, Bounding boxes)
      evidence: inspectionData.evidence || {
        image_urls: [],
        thumbnail_base64: null,
        ocr_extracted_text: '',
        is_360_scan: false
      },

      // Offline & Sync Metadata
      sync_status: inspectionData.sync_status || SYNC_STATUS.PENDING,
      sync_attempts: inspectionData.sync_attempts || 0,
      last_sync_error: inspectionData.last_sync_error || null,
      created_at: inspectionData.created_at || now,
      updated_at: now,
      synced_at: inspectionData.synced_at || null,
      
      // Metadata (Officer info, GPS location, device)
      officer_id: inspectionData.officer_id || 'OFFICER-DEFAULT',
      location: inspectionData.location || { latitude: null, longitude: null, district: 'Rural Zone' },
      device_info: inspectionData.device_info || {
        userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'Unknown Device',
        platform: typeof navigator !== 'undefined' ? navigator.platform : 'Unknown'
      },
      raw_payload: inspectionData.raw_payload || null
    };

    const request = store.put(record);

    request.onsuccess = () => {
      console.log(`[IndexedDB] Inspection saved locally [${record.inspection_id}] - Status: ${record.sync_status}`);
      resolve(record);
    };

    request.onerror = (event) => {
      console.error(`[IndexedDB] Failed to save inspection [${record.inspection_id}]:`, event.target.error);
      reject(event.target.error);
    };
  });
}

/**
 * Get inspection by ID
 * @param {string} inspectionId 
 * @returns {Promise<Object|null>}
 */
export async function getInspectionById(inspectionId) {
  const db = await initDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORES.INSPECTIONS], 'readonly');
    const store = transaction.objectStore(STORES.INSPECTIONS);
    const request = store.get(inspectionId);

    request.onsuccess = () => {
      resolve(request.result || null);
    };

    request.onerror = (event) => {
      reject(event.target.error);
    };
  });
}

/**
 * Get all inspections stored in local IndexedDB
 * @returns {Promise<Array<Object>>}
 */
export async function getAllInspections() {
  const db = await initDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORES.INSPECTIONS], 'readonly');
    const store = transaction.objectStore(STORES.INSPECTIONS);
    const request = store.getAll();

    request.onsuccess = () => {
      // Sort newest first
      const results = (request.result || []).sort((a, b) => {
        return new Date(b.created_at) - new Date(a.created_at);
      });
      resolve(results);
    };

    request.onerror = (event) => {
      reject(event.target.error);
    };
  });
}

/**
 * Get inspections by sync status ('pending', 'synced', 'failed')
 * @param {string} status 
 * @returns {Promise<Array<Object>>}
 */
export async function getInspectionsByStatus(status) {
  const db = await initDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORES.INSPECTIONS], 'readonly');
    const store = transaction.objectStore(STORES.INSPECTIONS);
    const index = store.index('sync_status');
    const request = index.getAll(status);

    request.onsuccess = () => {
      resolve(request.result || []);
    };

    request.onerror = (event) => {
      reject(event.target.error);
    };
  });
}

/**
 * Get all pending inspections that need to be synced
 * @returns {Promise<Array<Object>>}
 */
export async function getPendingInspections() {
  const db = await initDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORES.INSPECTIONS], 'readonly');
    const store = transaction.objectStore(STORES.INSPECTIONS);
    const index = store.index('sync_status');
    const request = index.getAll();

    request.onsuccess = () => {
      // Include both 'pending' and 'failed' (for retry)
      const pending = (request.result || []).filter(item => 
        item.sync_status === SYNC_STATUS.PENDING || item.sync_status === SYNC_STATUS.FAILED
      );
      resolve(pending);
    };

    request.onerror = (event) => {
      reject(event.target.error);
    };
  });
}

/**
 * Update the sync status of an inspection
 * @param {string} inspectionId 
 * @param {string} status ('synced' | 'pending' | 'failed' | 'syncing')
 * @param {string|null} errorMsg 
 * @param {string|null} cloudId 
 * @returns {Promise<Object>}
 */
export async function updateSyncStatus(inspectionId, status, errorMsg = null, cloudId = null) {
  const db = await initDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORES.INSPECTIONS, STORES.SYNC_LOG], 'readwrite');
    const inspectionStore = transaction.objectStore(STORES.INSPECTIONS);
    const logStore = transaction.objectStore(STORES.SYNC_LOG);

    const getReq = inspectionStore.get(inspectionId);

    getReq.onsuccess = () => {
      const record = getReq.result;
      if (!record) {
        return reject(new Error(`Inspection not found: ${inspectionId}`));
      }

      record.sync_status = status;
      record.updated_at = new Date().toISOString();

      if (status === SYNC_STATUS.SYNCED) {
        record.synced_at = new Date().toISOString();
        record.last_sync_error = null;
        if (cloudId) record.cloud_id = cloudId;
      } else if (status === SYNC_STATUS.FAILED) {
        record.sync_attempts = (record.sync_attempts || 0) + 1;
        record.last_sync_error = errorMsg || 'Unknown sync error';
      } else if (status === SYNC_STATUS.SYNCING) {
        record.sync_attempts = (record.sync_attempts || 0) + 1;
      }

      inspectionStore.put(record);

      // Audit log entry
      logStore.add({
        inspection_id: inspectionId,
        status: status,
        error: errorMsg,
        timestamp: new Date().toISOString()
      });

      resolve(record);
    };

    getReq.onerror = (event) => {
      reject(event.target.error);
    };
  });
}

/**
 * Find previous inspections for the same product (for MRP/Shrinkflation comparison)
 * @param {string} productName 
 * @returns {Promise<Array<Object>>}
 */
export async function getInspectionsByProduct(productName) {
  const db = await initDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORES.INSPECTIONS], 'readonly');
    const store = transaction.objectStore(STORES.INSPECTIONS);
    const index = store.index('product_name');
    const request = index.getAll(productName);

    request.onsuccess = () => {
      const results = (request.result || []).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      resolve(results);
    };

    request.onerror = (event) => {
      reject(event.target.error);
    };
  });
}

/**
 * Cache offline assets (e.g. 360 demo video, product master catalogue)
 * @param {string} key 
 * @param {any} data 
 * @returns {Promise<void>}
 */
export async function cacheOfflineAsset(key, data) {
  const db = await initDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORES.OFFLINE_CACHE], 'readwrite');
    const store = transaction.objectStore(STORES.OFFLINE_CACHE);
    const request = store.put({ key, data, cached_at: new Date().toISOString() });

    request.onsuccess = () => resolve();
    request.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Retrieve cached offline asset
 * @param {string} key 
 * @returns {Promise<any>}
 */
export async function getOfflineAsset(key) {
  const db = await initDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORES.OFFLINE_CACHE], 'readonly');
    const store = transaction.objectStore(STORES.OFFLINE_CACHE);
    const request = store.get(key);

    request.onsuccess = () => resolve(request.result ? request.result.data : null);
    request.onerror = (e) => reject(e.target.error);
  });
}

/**
 * Get sync statistics for dashboard badges
 * @returns {Promise<{total: number, pending: number, synced: number, failed: number, lastSyncTime: string|null}>}
 */
export async function getSyncStats() {
  const all = await getAllInspections();
  const pending = all.filter(i => i.sync_status === SYNC_STATUS.PENDING).length;
  const synced = all.filter(i => i.sync_status === SYNC_STATUS.SYNCED).length;
  const failed = all.filter(i => i.sync_status === SYNC_STATUS.FAILED).length;
  
  const lastSyncedRecord = all
    .filter(i => i.synced_at)
    .sort((a, b) => new Date(b.synced_at) - new Date(a.synced_at))[0];

  return {
    total: all.length,
    pending,
    synced,
    failed,
    lastSyncTime: lastSyncedRecord ? lastSyncedRecord.synced_at : null
  };
}

/**
 * Clear all inspections (Useful for testing reset)
 */
export async function clearAllInspections() {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction([STORES.INSPECTIONS, STORES.SYNC_LOG], 'readwrite');
    tx.objectStore(STORES.INSPECTIONS).clear();
    tx.objectStore(STORES.SYNC_LOG).clear();
    tx.oncomplete = () => resolve(true);
    tx.onerror = (e) => reject(e.target.error);
  });
}
