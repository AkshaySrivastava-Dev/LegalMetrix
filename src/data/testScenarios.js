/**
 * 13 Complete Test Scenarios for Legal Metrology System
 * Member 5 - Offline Database + Sync + Voice + Testing Engineer
 */

import mockData from './mockInspections.json' with { type: 'json' };

export const TEST_SCENARIOS = {
  COMPLIANT_PRODUCT: 1,
  NON_COMPLIANT_PRODUCT: 2,
  BLURRY_IMAGE: 3,
  DARK_IMAGE: 4,
  LOW_CONFIDENCE_OCR: 5,
  MANUAL_REVIEW: 6,
  SCAN_360_VIDEO: 7,
  PHYSICAL_ONLINE_MISMATCH: 8,
  SAME_PRODUCT_CHANGED_MRP: 9,
  OFFLINE_INSPECTION: 10,
  SYNC_AFTER_INTERNET_RETURNS: 11,
  FAILED_SYNC: 12,
  DUPLICATE_SYNC: 13
};

/**
 * Retrieve test case by scenario ID (1 to 13)
 * @param {number} scenarioId 
 * @returns {Object}
 */
export function getTestScenario(scenarioId) {
  return mockData.find(item => item.scenario_id === scenarioId) || null;
}

/**
 * Retrieve all 13 test scenarios
 * @returns {Array<Object>}
 */
export function getAllTestScenarios() {
  return mockData;
}
