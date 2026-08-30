-- =============================================================================
-- LegalMetrix AI - Supabase PostgreSQL Free Tier Schema & Policies
-- Designed for Smart India Hackathon 2026 Free Tier Deployment
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS public.inspections (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    category TEXT NOT NULL DEFAULT 'food',
    status TEXT NOT NULL DEFAULT 'COMPLIANT',
    product_name TEXT,
    brand TEXT,
    mrp TEXT,
    net_quantity TEXT,
    manufacturer TEXT,
    country_of_origin TEXT,
    manufacturing_date TEXT,
    expiry_date TEXT,
    batch_number TEXT,
    barcode TEXT,
    overall_confidence NUMERIC(4, 3) DEFAULT 0.000,
    is_offline BOOLEAN DEFAULT false,
    sync_status TEXT DEFAULT 'SYNCED',
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    reviewer_id TEXT,
    
    fields_payload JSONB DEFAULT '{}'::jsonb,
    compliance_payload JSONB DEFAULT '{}'::jsonb,
    safety_payload JSONB DEFAULT '{}'::jsonb,
    health_payload JSONB DEFAULT '{}'::jsonb,
    fraud_payload JSONB DEFAULT '{}'::jsonb,
    quality_payload JSONB DEFAULT '{}'::jsonb,
    image_urls JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS public.inspection_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    inspection_id TEXT REFERENCES public.inspections(id) ON DELETE CASCADE,
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    reviewer_id TEXT NOT NULL,
    field TEXT NOT NULL,
    action TEXT NOT NULL,
    ai_value TEXT,
    corrected_value TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_inspections_created_at ON public.inspections(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inspections_brand ON public.inspections(brand);
CREATE INDEX IF NOT EXISTS idx_inspections_status ON public.inspections(status);
CREATE INDEX IF NOT EXISTS idx_inspections_sync_status ON public.inspections(sync_status);

ALTER TABLE public.inspections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inspection_reviews ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access" ON public.inspections
    FOR SELECT USING (true);

CREATE POLICY "Allow public insert access" ON public.inspections
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow public update access" ON public.inspections
    FOR UPDATE USING (true);

CREATE POLICY "Allow public reviews read" ON public.inspection_reviews
    FOR SELECT USING (true);

CREATE POLICY "Allow public reviews insert" ON public.inspection_reviews
    FOR INSERT WITH CHECK (true);
