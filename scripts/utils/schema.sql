-- ============================================================================
-- UJIAN AKHIR SEMESTER (UAS) - TRENDING TOPICS ON STATISTICS 2026
-- SUPABASE POSTGRESQL + PGVECTOR SECURITY HARDENED SCHEMA (CRAG PMB UII)
-- ============================================================================

-- 1. Create extensions schema & enable pgvector extension safely
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- Move vector extension to extensions schema if previously in public (Fixes 0014_extension_in_public)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector' AND extnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')) THEN
        ALTER EXTENSION vector SET SCHEMA extensions;
    END IF;
END $$;

-- 2. Table DDL: pmb_sections
CREATE TABLE IF NOT EXISTS public.pmb_sections (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    doc_id CHARACTER VARYING(50) NOT NULL,
    module CHARACTER VARYING(50) NOT NULL,
    section_title TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    preprocessed_text TEXT NOT NULL,
    embedding extensions.vector(768) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    CONSTRAINT pmb_sections_pkey PRIMARY KEY (id),
    CONSTRAINT pmb_sections_doc_id_key UNIQUE (doc_id)
);

-- HNSW Vector Index for High-Performance Cosine Search
CREATE INDEX IF NOT EXISTS pmb_vector_cosine_idx 
ON public.pmb_sections USING hnsw (embedding extensions.vector_cosine_ops)
WITH (m = '16', ef_construction = '64');

-- Enable Row Level Security (RLS) for pmb_sections
ALTER TABLE public.pmb_sections ENABLE ROW LEVEL SECURITY;

-- Security Policies for pmb_sections (Public SELECT, Admin/Service FULL ACCESS)
DROP POLICY IF EXISTS "Public Read Access for PMB Sections" ON public.pmb_sections;
DROP POLICY IF EXISTS "Service Role Full Access for PMB Sections" ON public.pmb_sections;
DROP POLICY IF EXISTS "Full Access for PMB Sections" ON public.pmb_sections;

-- Public roles (anon & authenticated) can ONLY READ / SELECT documents
CREATE POLICY "Public Read Access for PMB Sections" 
ON public.pmb_sections FOR SELECT 
TO anon, authenticated, service_role 
USING (true);

-- Full management access reserved strictly for service_role / internal scripts
CREATE POLICY "Service Role Full Access for PMB Sections" 
ON public.pmb_sections FOR ALL 
TO service_role 
USING (true) WITH CHECK (true);

-- 3. Table DDL: crag_logs
CREATE TABLE IF NOT EXISTS public.crag_logs (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    user_query TEXT NOT NULL,
    decision_path CHARACTER VARYING(50) NOT NULL,
    confidence_label CHARACTER VARYING(50) NOT NULL,
    rewritten_query TEXT NULL,
    top_score DOUBLE PRECISION NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL,
    answer_generated TEXT NOT NULL,
    citations_count INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    CONSTRAINT crag_logs_pkey PRIMARY KEY (id)
);

-- Enable Row Level Security (RLS) for crag_logs
ALTER TABLE public.crag_logs ENABLE ROW LEVEL SECURITY;

-- Security Policies for crag_logs (Fixes 0024_permissive_rls_policy)
DROP POLICY IF EXISTS "Public Full Access for CRAG Logs" ON public.crag_logs;
DROP POLICY IF EXISTS "Allow Public Insert for CRAG Logs" ON public.crag_logs;
DROP POLICY IF EXISTS "Service Role Full Access for CRAG Logs" ON public.crag_logs;

-- Allow public roles ONLY to insert valid logs with non-empty query check (Fixes 0024 permissive check)
CREATE POLICY "Allow Public Insert for CRAG Logs" 
ON public.crag_logs FOR INSERT 
TO anon, authenticated 
WITH CHECK (length(user_query) > 0);

-- Full access reserved strictly for service_role / admins
CREATE POLICY "Service Role Full Access for CRAG Logs" 
ON public.crag_logs FOR ALL 
TO service_role 
USING (true) WITH CHECK (true);

-- 4. Stored Procedure: match_pmb_sections (Fixes 0011_function_search_path_mutable)
CREATE OR REPLACE FUNCTION public.match_pmb_sections (
    query_embedding extensions.vector(768),
    match_threshold FLOAT DEFAULT 0.20,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    doc_id VARCHAR(50),
    module VARCHAR(50),
    section_title TEXT,
    raw_text TEXT,
    preprocessed_text TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
SET search_path = public, extensions, pg_temp
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pmb_sections.id,
        pmb_sections.doc_id,
        pmb_sections.module,
        pmb_sections.section_title,
        pmb_sections.raw_text,
        pmb_sections.preprocessed_text,
        1 - (pmb_sections.embedding <=> query_embedding) AS similarity
    FROM public.pmb_sections
    WHERE 1 - (pmb_sections.embedding <=> query_embedding) >= match_threshold
    ORDER BY pmb_sections.embedding <=> query_embedding ASC
    LIMIT match_count;
END;
$$;

-- 5. Revoke Execution Privileges on Security Definer Functions (Fixes 0028 & 0029)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'rls_auto_enable') THEN
        REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated;
        GRANT EXECUTE ON FUNCTION public.rls_auto_enable() TO service_role;
    END IF;
END $$;
