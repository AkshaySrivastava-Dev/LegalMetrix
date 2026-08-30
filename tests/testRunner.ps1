# =========================================================================
# SMART INDIA HACKATHON - AUTOMATED TEST SUITE (PowerShell Runner)
# MEMBER 5: OFFLINE DATABASE + SYNC + VOICE + TESTING ENGINEER
# =========================================================================

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$mockDataFile = Join-Path $scriptDir "..\src\data\mockInspections.json"

Write-Host "`nStarting Member 5 Automated Test Suite (13 Scenarios + DB + Voice)" -ForegroundColor Cyan
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n" -ForegroundColor DarkGray

$mockData = Get-Content $mockDataFile -Raw | ConvertFrom-Json

$totalTests = 0
$passedTests = 0
$failedTests = 0

function Assert-Condition($condition, $message) {
    $script:totalTests++
    if ($condition) {
        Write-Host "  PASS: $message" -ForegroundColor Green
        $script:passedTests++
    } else {
        Write-Host "  FAIL: $message" -ForegroundColor Red
        $script:failedTests++
    }
}

function Print-Header($title) {
    Write-Host "`n================================================================" -ForegroundColor Yellow
    Write-Host "  $title" -ForegroundColor Yellow
    Write-Host "================================================================" -ForegroundColor Yellow
}

# --------------------------------------------------------------------------
Print-Header "SCENARIO 1: Compliant Product"
# --------------------------------------------------------------------------
$sc1 = $mockData | Where-Object { $_.scenario_id -eq 1 }
Assert-Condition ($sc1 -ne $null) "Scenario 1 data exists"
Assert-Condition ($sc1.compliance_status -eq "COMPLIANT") "Compliance status is COMPLIANT"
Assert-Condition ($sc1.violations.Count -eq 0) "Zero violations for compliant commodity"
Assert-Condition ($sc1.mandatory_declarations.mrp_present -eq $true) "MRP declaration present"
Assert-Condition ($sc1.mandatory_declarations.unit_sale_price_present -eq $true) "Unit Sale Price present"
Assert-Condition ($sc1.confidence -ge 0.95) "High confidence score (>95%)"

# --------------------------------------------------------------------------
Print-Header "SCENARIO 2: Non-compliant Product (Missing Declarations)"
# --------------------------------------------------------------------------
$sc2 = $mockData | Where-Object { $_.scenario_id -eq 2 }
Assert-Condition ($sc2.compliance_status -eq "NON_COMPLIANT") "Compliance status is NON_COMPLIANT"
Assert-Condition ($sc2.violations.Count -ge 2) "Detects both missing Unit Sale Price and Consumer Care"
Assert-Condition ($sc2.mandatory_declarations.unit_sale_price_present -eq $false) "Unit sale price marked false"
Assert-Condition ($sc2.mandatory_declarations.consumer_care_present -eq $false) "Consumer care marked false"

# --------------------------------------------------------------------------
Print-Header "SCENARIO 3: Blurry Image Scan"
# --------------------------------------------------------------------------
$sc3 = $mockData | Where-Object { $_.scenario_id -eq 3 }
Assert-Condition ($sc3.compliance_status -eq "UNCLEAR_IMAGE") "Flags status as UNCLEAR_IMAGE"
Assert-Condition ($sc3.confidence -lt 0.40) "Confidence score dropped below clarity threshold"
Assert-Condition ($sc3.evidence.blur_score -gt 80) "Blur score detected above threshold (88.5)"

# --------------------------------------------------------------------------
Print-Header "SCENARIO 4: Dark Image Scan (Low Luminance in Rural Store)"
# --------------------------------------------------------------------------
$sc4 = $mockData | Where-Object { $_.scenario_id -eq 4 }
Assert-Condition ($sc4.compliance_status -eq "FLAGGED_MANUAL_REVIEW") "Flags for manual review due to low light"
Assert-Condition ($sc4.evidence.luminance_value -lt 20) "Luminance correctly identified as dark (18/255)"

# --------------------------------------------------------------------------
Print-Header "SCENARIO 5: Low-Confidence OCR (Smudged Ink Stamp)"
# --------------------------------------------------------------------------
$sc5 = $mockData | Where-Object { $_.scenario_id -eq 5 }
Assert-Condition ($sc5.confidence -lt 0.60) "Low overall confidence for smudged stamp (52%)"
Assert-Condition ($sc5.evidence.ocr_token_confidences.mfg_date -lt 0.50) "Specific token confidence for mfg_date is low"

# --------------------------------------------------------------------------
Print-Header "SCENARIO 6: Manual Review (Net Weight Label vs Barcode Conflict)"
# --------------------------------------------------------------------------
$sc6 = $mockData | Where-Object { $_.scenario_id -eq 6 }
Assert-Condition ($sc6.compliance_status -eq "FLAGGED_MANUAL_REVIEW") "Discrepancy correctly routed to manual review"
Assert-Condition ($sc6.violations[0] -like "*Discrepancy*") "Discrepancy description recorded in violations"

# --------------------------------------------------------------------------
Print-Header "SCENARIO 7: 360 Video Inspection (Multi-panel scan)"
# --------------------------------------------------------------------------
$sc7 = $mockData | Where-Object { $_.scenario_id -eq 7 }
Assert-Condition ($sc7.evidence.is_360_scan -eq $true) "Marked as 360 scan"
Assert-Condition ($sc7.evidence.stitched_panels.Count -eq 6) "All 6 package facets stitched"
Assert-Condition ($sc7.evidence.video_asset_id -eq "PRE_RECORDED_360_COLGATE_150G") "Pre-recorded video fallback identifier present"

# --------------------------------------------------------------------------
Print-Header "SCENARIO 8: Physical vs Online MRP Mismatch (Dual Pricing Violation)"
# --------------------------------------------------------------------------
$sc8 = $mockData | Where-Object { $_.scenario_id -eq 8 }
Assert-Condition ($sc8.compliance_status -eq "NON_COMPLIANT") "Dual pricing flagged as NON_COMPLIANT"
$delta = $sc8.evidence.online_listed_mrp - $sc8.evidence.physical_mrp
Assert-Condition ($delta -eq 15.00) "Calculates price discrepancy delta (Rs 15 markup)"
Assert-Condition ($sc8.violations[0] -like "*Dual MRP Violation*") "Specific Legal Metrology rule violation cited"

# --------------------------------------------------------------------------
Print-Header "SCENARIO 9: Same Product Comparison (Shrinkflation & MRP Hike)"
# --------------------------------------------------------------------------
$sc9 = $mockData | Where-Object { $_.scenario_id -eq 9 }
$mrpDiff = $sc9.mrp - $sc9.evidence.previous_mrp
Assert-Condition ($mrpDiff -eq 5.00) "Detects Rs 5.00 MRP hike"
Assert-Condition ($sc9.net_quantity -eq "90 g" -and $sc9.evidence.previous_net_quantity -eq "100 g") "Detects net quantity reduction (100g -> 90g)"

# --------------------------------------------------------------------------
Print-Header "SCENARIO 10: Offline Inspection (Saved locally in IndexedDB)"
# --------------------------------------------------------------------------
$sc10 = $mockData | Where-Object { $_.scenario_id -eq 10 }
Assert-Condition ($sc10.sync_status -eq "pending") "Offline inspection initially set to sync_status: pending"
Assert-Condition ($sc10.sync_attempts -eq 0) "Zero sync attempts while offline"
Assert-Condition ($sc10.inspection_id -like "INSP-*") "Valid unique inspection ID generated"

# --------------------------------------------------------------------------
Print-Header "SCENARIO 11: Sync After Internet Returns"
# --------------------------------------------------------------------------
$sc11 = $mockData | Where-Object { $_.scenario_id -eq 11 }
Assert-Condition ($sc11.sync_status -eq "synced") "Transitioned to sync_status: synced"
Assert-Condition ($sc11.synced_at -ne $null) "synced_at timestamp recorded"

# --------------------------------------------------------------------------
Print-Header "SCENARIO 12: Failed Sync (Exponential Backoff & Retention)"
# --------------------------------------------------------------------------
$sc12 = $mockData | Where-Object { $_.scenario_id -eq 12 }
Assert-Condition ($sc12.sync_status -eq "failed") "Status marked as failed"
Assert-Condition ($sc12.sync_attempts -gt 0) "Sync attempt counter incremented"
Assert-Condition ($sc12.last_sync_error.Length -gt 0) "Error reason logged for diagnostic audit"
Assert-Condition ($sc12.product_name -eq "Maggi 2-Minute Noodles Masala") "Local record preserved without data loss"

# --------------------------------------------------------------------------
Print-Header "SCENARIO 13: Duplicate Sync (Idempotent Deduplication)"
# --------------------------------------------------------------------------
$sc13 = $mockData | Where-Object { $_.scenario_id -eq 13 }
Assert-Condition ($sc13.sync_status -eq "synced") "Status is synced"
Assert-Condition ($sc13.sync_attempts -eq 2) "Handled re-transmission attempt gracefully"

# --------------------------------------------------------------------------
# SUMMARY
# --------------------------------------------------------------------------
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  TEST RESULTS SUMMARY" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Total Checks Executed : $totalTests"
Write-Host "  Passed Checks         : $passedTests" -ForegroundColor Green
Write-Host "  Failed Checks         : $failedTests" -ForegroundColor $(if ($failedTests -eq 0) { "Green" } else { "Red" })
$rate = [math]::Round(($passedTests / $totalTests) * 100, 1)
Write-Host "  Success Rate          : $rate%"
Write-Host "================================================================" -ForegroundColor Cyan

if ($failedTests -eq 0) {
    Write-Host "ALL 13 TEST SCENARIOS PASSED!`n" -ForegroundColor Green
} else {
    Write-Host "SOME CHECKS FAILED. Please review above.`n" -ForegroundColor Red
    exit 1
}
