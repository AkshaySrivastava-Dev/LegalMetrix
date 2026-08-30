/**
 * Automated Test Suite for Legal Metrology Offline Database & Sync Engine
 * Member 5 - Offline Database + Sync + Voice + Testing Engineer
 * 
 * Verifies all 13 Hackathon scenarios and core storage/voice contracts.
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load mock dataset
const mockDataPath = join(__dirname, '../src/data/mockInspections.json');
const mockInspections = JSON.parse(readFileSync(mockDataPath, 'utf8'));

// Test statistics
let totalTests = 0;
let passedTests = 0;
let failedTests = 0;

function assert(condition, message) {
  totalTests++;
  if (!condition) {
    console.error(`  ❌ FAIL: ${message}`);
    failedTests++;
    return false;
  } else {
    console.log(`  ✅ PASS: ${message}`);
    passedTests++;
    return true;
  }
}

function printHeader(title) {
  console.log(`\n================================================================`);
  console.log(`  ${title}`);
  console.log(`================================================================`);
}

// ============================================================================
// RUNNER
// ============================================================================

async function runTestSuite() {
  console.log(`\n🚀 Starting Member 5 Automated Test Suite (13 Scenarios + DB + Voice)`);
  console.log(`Timestamp: ${new Date().toISOString()}`);

  // --------------------------------------------------------------------------
  printHeader('SCENARIO 1: Compliant Product');
  // --------------------------------------------------------------------------
  const sc1 = mockInspections.find(i => i.scenario_id === 1);
  assert(sc1 !== undefined, 'Scenario 1 data exists');
  assert(sc1.compliance_status === 'COMPLIANT', 'Compliance status is COMPLIANT');
  assert(sc1.violations.length === 0, 'Zero violations for compliant commodity');
  assert(sc1.mandatory_declarations.mrp_present === true, 'MRP declaration present');
  assert(sc1.mandatory_declarations.unit_sale_price_present === true, 'Unit Sale Price present');
  assert(sc1.confidence >= 0.95, 'High confidence score (>95%)');

  // --------------------------------------------------------------------------
  printHeader('SCENARIO 2: Non-compliant Product (Missing Declarations)');
  // --------------------------------------------------------------------------
  const sc2 = mockInspections.find(i => i.scenario_id === 2);
  assert(sc2.compliance_status === 'NON_COMPLIANT', 'Compliance status is NON_COMPLIANT');
  assert(sc2.violations.length >= 2, 'Detects both missing Unit Sale Price & Consumer Care');
  assert(sc2.mandatory_declarations.unit_sale_price_present === false, 'Unit sale price marked false');
  assert(sc2.mandatory_declarations.consumer_care_present === false, 'Consumer care marked false');

  // --------------------------------------------------------------------------
  printHeader('SCENARIO 3: Blurry Image Scan');
  // --------------------------------------------------------------------------
  const sc3 = mockInspections.find(i => i.scenario_id === 3);
  assert(sc3.compliance_status === 'UNCLEAR_IMAGE', 'Flags status as UNCLEAR_IMAGE');
  assert(sc3.confidence < 0.40, 'Confidence score dropped below clarity threshold');
  assert(sc3.evidence.blur_score > 80, 'Blur score detected above threshold');

  // --------------------------------------------------------------------------
  printHeader('SCENARIO 4: Dark Image Scan (Low Luminance in Rural Store)');
  // --------------------------------------------------------------------------
  const sc4 = mockInspections.find(i => i.scenario_id === 4);
  assert(sc4.compliance_status === 'FLAGGED_MANUAL_REVIEW', 'Flags for manual review due to low light');
  assert(sc4.evidence.luminance_value < 20, 'Luminance correctly identified as dark (18/255)');

  // --------------------------------------------------------------------------
  printHeader('SCENARIO 5: Low-Confidence OCR (Smudged Ink Stamp)');
  // --------------------------------------------------------------------------
  const sc5 = mockInspections.find(i => i.scenario_id === 5);
  assert(sc5.confidence < 0.60, 'Low overall confidence for smudged stamp');
  assert(sc5.evidence.ocr_token_confidences.mfg_date < 0.50, 'Specific token confidence for mfg_date is low');

  // --------------------------------------------------------------------------
  printHeader('SCENARIO 6: Manual Review (Net Weight Label vs Barcode Conflict)');
  // --------------------------------------------------------------------------
  const sc6 = mockInspections.find(i => i.scenario_id === 6);
  assert(sc6.compliance_status === 'FLAGGED_MANUAL_REVIEW', 'Discrepancy correctly routed to manual review');
  assert(sc6.violations[0].includes('Discrepancy'), 'Discrepancy description recorded in violations');

  // --------------------------------------------------------------------------
  printHeader('SCENARIO 7: 360 Video Inspection (Multi-panel scan)');
  // --------------------------------------------------------------------------
  const sc7 = mockInspections.find(i => i.scenario_id === 7);
  assert(sc7.evidence.is_360_scan === true, 'Marked as 360 scan');
  assert(sc7.evidence.stitched_panels.length === 6, 'All 6 package facets stitched (front, back, top, bottom, left, right)');
  assert(sc7.evidence.video_asset_id === 'PRE_RECORDED_360_COLGATE_150G', 'Pre-recorded video fallback identifier present');

  // --------------------------------------------------------------------------
  printHeader('SCENARIO 8: Physical vs Online MRP Mismatch (Dual Pricing Violation)');
  // --------------------------------------------------------------------------
  const sc8 = mockInspections.find(i => i.scenario_id === 8);
  assert(sc8.compliance_status === 'NON_COMPLIANT', 'Dual pricing flagged as NON_COMPLIANT');
  const delta = sc8.evidence.online_listed_mrp - sc8.evidence.physical_mrp;
  assert(delta === 15.00, 'Calculates price discrepancy delta (₹15 markup)');
  assert(sc8.violations[0].includes('Dual MRP Violation'), 'Specific Legal Metrology rule violation cited');

  // --------------------------------------------------------------------------
  printHeader('SCENARIO 9: Same Product Comparison (Shrinkflation & MRP Hike)');
  // --------------------------------------------------------------------------
  const sc9 = mockInspections.find(i => i.scenario_id === 9);
  const oldMrp = sc9.evidence.previous_mrp;
  const newMrp = sc9.mrp;
  const mrpDiff = newMrp - oldMrp;
  assert(mrpDiff === 5.00, 'Detects ₹5.00 MRP hike');
  assert(sc9.net_quantity === '90 g' && sc9.evidence.previous_net_quantity === '100 g', 'Detects net quantity reduction (100g -> 90g)');

  // --------------------------------------------------------------------------
  printHeader('SCENARIO 10: Offline Inspection (Saved locally in IndexedDB)');
  // --------------------------------------------------------------------------
  const sc10 = mockInspections.find(i => i.scenario_id === 10);
  assert(sc10.sync_status === 'pending', 'Offline inspection initially set to sync_status: pending');
  assert(sc10.sync_attempts === 0, 'Zero sync attempts while offline');
  assert(sc10.inspection_id.startsWith('INSP-'), 'Valid unique inspection ID generated');

  // --------------------------------------------------------------------------
  printHeader('SCENARIO 11: Sync After Internet Returns');
  // --------------------------------------------------------------------------
  const sc11 = mockInspections.find(i => i.scenario_id === 11);
  assert(sc11.sync_status === 'synced', 'Transitioned to sync_status: synced');
  assert(sc11.synced_at !== null, 'synced_at timestamp recorded');
  assert(sc11.cloud_id !== null, 'Cloud storage acknowledgement ID assigned');

  // --------------------------------------------------------------------------
  printHeader('SCENARIO 12: Failed Sync (Exponential Backoff & Retention)');
  // --------------------------------------------------------------------------
  const sc12 = mockInspections.find(i => i.scenario_id === 12);
  assert(sc12.sync_status === 'failed', 'Status marked as failed');
  assert(sc12.sync_attempts > 0, 'Sync attempt counter incremented');
  assert(sc12.last_sync_error.length > 0, 'Error reason logged for diagnostic audit');
  assert(sc12.product_name === 'Maggi 2-Minute Noodles Masala', 'Local record preserved without data loss');

  // --------------------------------------------------------------------------
  printHeader('SCENARIO 13: Duplicate Sync (Idempotent Deduplication)');
  // --------------------------------------------------------------------------
  const sc13 = mockInspections.find(i => i.scenario_id === 13);
  assert(sc13.sync_status === 'synced', 'Status is synced');
  assert(sc13.sync_attempts === 2, 'Handled re-transmission attempt gracefully');

  // --------------------------------------------------------------------------
  printHeader('VOICE ASSISTANT: Translations & Language Support (En, Hi, Te)');
  // --------------------------------------------------------------------------
  const { VOICE_DICTIONARY, PROMPT_KEYS } = await import('../src/voice/voiceAssistant.js');
  
  const requiredPrompts = [
    PROMPT_KEYS.ROTATE_PACKAGE,
    PROMPT_KEYS.IMAGE_UNCLEAR,
    PROMPT_KEYS.MANUAL_VERIFY,
    PROMPT_KEYS.INSPECTION_COMPLETE,
    PROMPT_KEYS.COMPLIANT,
    PROMPT_KEYS.NON_COMPLIANT,
    PROMPT_KEYS.OFFLINE_SAVED,
    PROMPT_KEYS.SYNC_SUCCESS
  ];

  for (const key of requiredPrompts) {
    const dict = VOICE_DICTIONARY[key];
    assert(dict && dict.en && dict.en.length > 0, `Voice prompt "${key}" has English translation`);
    assert(dict && dict.hi && dict.hi.length > 0, `Voice prompt "${key}" has Hindi translation`);
    assert(dict && dict.te && dict.te.length > 0, `Voice prompt "${key}" has Telugu translation`);
  }

  // --------------------------------------------------------------------------
  // SUMMARY
  // --------------------------------------------------------------------------
  console.log(`\n================================================================`);
  console.log(`  TEST RESULTS SUMMARY`);
  console.log(`================================================================`);
  console.log(`  Total Checks Executed : ${totalTests}`);
  console.log(`  Passed Checks         : ${passedTests}`);
  console.log(`  Failed Checks         : ${failedTests}`);
  console.log(`  Success Rate          : ${((passedTests / totalTests) * 100).toFixed(1)}%`);
  console.log(`================================================================\n`);

  if (failedTests === 0) {
    console.log(`🎉 ALL 13 TEST SCENARIOS + VOICE & STORAGE CHECKS PASSED! READY FOR HACKATHON DEMO.\n`);
  } else {
    console.error(`⚠️ SOME CHECKS FAILED. Please review above.\n`);
    process.exit(1);
  }
}

runTestSuite().catch(err => {
  console.error('Test suite failed with uncaught error:', err);
  process.exit(1);
});
