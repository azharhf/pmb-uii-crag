-- ==============================================================================
-- SUPABASE DATABASE KEEP-ALIVE CRON JOB (PREVENT AUTO-PAUSE & SUSPEND)
-- Jalankan skrip ini di Supabase Dashboard -> SQL Editor
-- ==============================================================================

-- 1. Aktifkan ekstensi pg_cron bawaan PostgreSQL Supabase
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 2. Buat tabel pemicu ping sederhana
CREATE TABLE IF NOT EXISTS public._supabase_keep_alive (
    id SERIAL PRIMARY KEY,
    last_ping TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Buat fungsi plpgsql untuk menjalankan transaksi aktif secara berkala
CREATE OR REPLACE FUNCTION public.ping_keep_alive()
RETURNS VOID AS $$
BEGIN
    INSERT INTO public._supabase_keep_alive (last_ping) VALUES (NOW());
    DELETE FROM public._supabase_keep_alive WHERE last_ping < NOW() - INTERVAL '3 days';
END;
$$ LANGUAGE plpgsql;

-- 4. Jadwalkan cron job internal setiap 2 hari sekali (Jam 00:00 UTC)
-- Format Cron: Minute Hour DayOfMonth Month DayOfWeek
SELECT cron.schedule(
    'keep-alive-supabase-ping',
    '0 0 */2 * *',
    'SELECT public.ping_keep_alive();'
);

-- 5. Query verifikasi untuk mengecek daftar cron job yang aktif
SELECT * FROM cron.job;
